import streamlit as st
import pandas as pd
import google.generativeai as genai
import folium
import streamlit.components.v1 as components

# --- 1. 系統設定 ---
st.set_page_config(page_title="PetMatch AI", page_icon="🐾", layout="centered")

# ====== 🔑 API KEY 設定區 (請在此填入您的新 KEY) ======
# 請將下方的 "貼上您的新KEY" 換成您的 API Key
GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
# ===================================================

# --- 2. 讀取 Excel ---
@st.cache_data
def load_hospitals():
    try:
        df = pd.read_excel("hospitals.xlsx")
        df['tags'] = df['tags'].fillna("").astype(str).apply(lambda x: x.split(','))
        return df
    except FileNotFoundError:
        return pd.DataFrame()
    except Exception as e:
        st.error(f"❌ 讀取 Excel 失敗：{e}")
        return pd.DataFrame()

df_hospitals = load_hospitals()
HOSPITALS_DB = df_hospitals.to_dict('records') if not df_hospitals.empty else []

# --- 3. 側邊欄 ---
with st.sidebar:
    st.title("🐾 PetMatch")
    
    if GOOGLE_API_KEY == "貼上您的新KEY" or not GOOGLE_API_KEY:
        st.error("⚠️ 請在第 12 行填入 API Key")
    else:
        st.success("✅ AI 系統已連線")
        
    st.markdown("---")
    
    st.markdown("### 📍 設定您的位置")
    user_city = st.selectbox(
        "選擇您所在的城市 (模擬 GPS)",
        ["台北市 (信義區)", "台中市 (西屯區)", "高雄市 (左營區)"]
    )
    
    user_coords = {
        "台北市 (信義區)": {"lat": 25.0330, "lon": 121.5654},
        "台中市 (西屯區)": {"lat": 24.1630, "lon": 120.6400},
        "高雄市 (左營區)": {"lat": 22.6800, "lon": 120.3000}
    }
    current_user_pos = user_coords[user_city]
    
    st.info(f"目前定位：**{user_city}**")

# --- 4. AI 核心 ---
def get_gemini_response(user_input):
    if GOOGLE_API_KEY == "貼上您的新KEY" or not GOOGLE_API_KEY:
        return "⚠️ 請先填入 API Key！", "low", "動物", "動物醫院"
    
    try:
        genai.configure(api_key=GOOGLE_API_KEY)
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        system_prompt = f"""
        Role: PetMatch Triage System.
        Task: Analyze input: "{user_input}"
        Strict Output Rules:
        1. Language: Traditional Chinese.
        2. Format Requirement:
        URGENCY: [HIGH/MEDIUM/LOW]
        RESPONSE: [Advice within 100 words.]
        ANIMAL_TYPE: [e.g., 爬蟲, 鳥類, 兔子]
        SEARCH_KEYWORDS: [e.g., 爬蟲 動物醫院, 24H 急診]

        Example:
        URGENCY: HIGH
        RESPONSE: 建議立即送醫。
        ANIMAL_TYPE: 爬蟲
        SEARCH_KEYWORDS: 爬蟲專科 24H 急診
        """
        response = model.generate_content(system_prompt)
        text = response.text
        
        urgency = "low"
        if "URGENCY: HIGH" in text: urgency = "high"
        elif "URGENCY: MEDIUM" in text: urgency = "medium"
        
        clean_reply = text.split("RESPONSE:")[-1].split("ANIMAL_TYPE:")[0].strip()
        animal_type = "特寵"
        
        if "ANIMAL_TYPE:" in text:
            animal_type = text.split("ANIMAL_TYPE:")[-1].split("SEARCH_KEYWORDS:")[0].strip()
            
        search_keywords = "動物醫院"
        if "SEARCH_KEYWORDS:" in text:
            search_keywords = text.split("SEARCH_KEYWORDS:")[-1].strip()

        return clean_reply, urgency, animal_type, search_keywords

    except Exception as e:
        return f"連線錯誤：{e}", "low", "動物", "動物醫院"

# --- 5. 介面呈現 ---
st.title("🐾 PetMatch 智慧醫療導航")

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "嗨！請告訴我寵物狀況，我會幫您配對最近的專科醫院。"}]

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

if prompt := st.chat_input("輸入症狀..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)

    with st.chat_message("assistant"):
        with st.spinner("🧠 AI 分析中..."):
            reply_text, urgency_level, animal_type, search_keywords = get_gemini_response(prompt)
            st.write(reply_text)
            st.session_state.messages.append({"role": "assistant", "content": reply_text})
            
            # Excel 篩選邏輯
            vip_hospitals = []
            if HOSPITALS_DB:
                for h in HOSPITALS_DB:
                    tags_str = str(h['tags'])
                    if animal_type in tags_str or any(k in tags_str for k in search_keywords.split()):
                        vip_hospitals.append(h)
                    if urgency_level == "high" and ("24H" in tags_str or "急診" in tags_str):
                        if h not in vip_hospitals: vip_hospitals.append(h)

            # --- 顯示中文地圖 ---
            m = folium.Map(location=[current_user_pos["lat"], current_user_pos["lon"]], zoom_start=14)
            bounds = [[current_user_pos["lat"], current_user_pos["lon"]]]

            folium.Marker(
                [current_user_pos["lat"], current_user_pos["lon"]],
                popup="您的位置",
                tooltip="您的位置",
                icon=folium.Icon(color="blue", icon="user")
            ).add_to(m)

            if vip_hospitals:
                hospital_color = "red" if urgency_level == "high" else "green"
                for h in vip_hospitals:
                    bounds.append([h['lat'], h['lon']])
                    popup_html = f"<b>{h['name']}</b><br>⭐ {h['rating']}"
                    folium.Marker(
                        [h['lat'], h['lon']],
                        popup=folium.Popup(popup_html, max_width=200),
                        tooltip=h['name'],
                        icon=folium.Icon(color=hospital_color, icon="plus")
                    ).add_to(m)

            if len(bounds) > 1:
                m.fit_bounds(bounds)

            map_html = m._repr_html_()
            components.html(map_html, height=400)

            # --- 顯示結果文字 ---
            if urgency_level == "high":
                st.error(f"🚨 高度緊急！(AI 建議搜尋：{search_keywords})")
            else:
                st.info(f"ℹ️ 醫療建議 (AI 判斷：{animal_type})")

            # --- 顯示醫院列表 ---
            if vip_hospitals:
                st.markdown(f"### 🏆 推薦專科醫院")
                for hospital in vip_hospitals:
                    st.markdown(f"**🏅 {hospital['name']}**")
                    st.caption(f"⭐ {hospital['rating']} | 📍 {hospital['status']}")
                    st.markdown("".join([f" `#{t.strip()}`" for t in hospital['tags']]))
                    
                    # === 修正部分：Google Maps 官方導航連結 ===
                    # 格式：https://www.google.com/maps/dir/?api=1&destination=緯度,經度
                    lat = hospital['lat']
                    lon = hospital['lon']
                    map_link = f"https://www.google.com/maps/dir/?api=1&destination={lat},{lon}"
                    
                    st.link_button("🚗 導航", map_link, type="primary")
                    st.divider()
            else:
                st.warning(f"附近暫無 Excel 認證的 **{animal_type}** 醫院。")

            st.markdown("### 🔍 搜尋附近資源")
            
            # === 修正部分：Google Maps 官方搜尋連結 ===
            # 格式：https://www.google.com/maps/search/?api=1&query=關鍵字
            gmap_query = f"https://www.google.com/maps/search/?api=1&query={search_keywords}"
            
            st.link_button(f"👉 在 Google Maps 搜尋「{search_keywords}」", gmap_query, type="secondary", use_container_width=True)