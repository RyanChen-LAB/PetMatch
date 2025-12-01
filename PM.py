import streamlit as st
import pandas as pd
import google.generativeai as genai
import folium
import streamlit.components.v1 as components
from streamlit_js_eval import get_geolocation # 記得安裝 pip install streamlit-js-eval
from math import radians, cos, sin, asin, sqrt

# --- 1. 頁面設定 ---
st.set_page_config(page_title="PetMatch AI智慧寵心導航", page_icon="🐾", layout="wide")

# ====== 🎨 CSS 美化魔法區 ======
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Noto Sans TC', sans-serif; }
    .stApp { background-color: #F8F9FA; }
    
    .hero-container {
        background: linear-gradient(135deg, #2A9D8F 0%, #264653 100%);
        padding: 40px 20px;
        border-radius: 0 0 20px 20px;
        color: white;
        text-align: center;
        margin-bottom: 30px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .hero-title { font-size: 2.5rem; font-weight: 700; margin: 0; }
    .hero-subtitle { font-size: 1.2rem; opacity: 0.9; margin-top: 10px; }

    div[data-testid="stVerticalBlock"] > div[style*="background-color"] {
        background-color: white !important;
        border-radius: 15px;
        padding: 20px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        border: 1px solid #E0E0E0;
    }
    
    .stButton > button {
        background-color: #2A9D8F;
        color: white;
        border-radius: 25px;
        border: none;
        padding: 10px 24px;
        font-weight: bold;
        width: 100%;
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        background-color: #21867a;
        transform: translateY(-2px);
    }
    
    .stChatMessage {
        background-color: #ffffff;
        border-radius: 15px;
        padding: 10px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)

# ====== 🔑 API KEY 設定區 ======
try:
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
except:
    GOOGLE_API_KEY = "" 
# ==============================

# --- 工具：計算距離 (Haversine Formula) ---
def calculate_distance(lat1, lon1, lat2, lon2):
    try:
        lon1, lat1, lon2, lat2 = map(radians, [float(lon1), float(lat1), float(lon2), float(lat2)])
        dlon = lon2 - lon1 
        dlat = lat2 - lat1 
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a)) 
        r = 6371 # 地球半徑 (km)
        return c * r
    except:
        return 9999

# --- 資料讀取 ---
@st.cache_data
def load_hospitals():
    try:
        df = pd.read_excel("hospitals.xlsx")
        df['tags'] = df['tags'].fillna("").astype(str).apply(lambda x: x.split(','))
        return df
    except:
        return pd.DataFrame()

df_hospitals = load_hospitals()
HOSPITALS_DB = df_hospitals.to_dict('records') if not df_hospitals.empty else []

# --- AI 核心 ---
def get_gemini_response(user_input):
    if not GOOGLE_API_KEY:
        return "⚠️ 請檢查 API Key 設定", "low", "動物", "動物醫院"
    
    try:
        genai.configure(api_key=GOOGLE_API_KEY)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        system_prompt = f"""
        Role: PetMatch Triage System.
        Task: Analyze input: "{user_input}"
        Strict Output Rules:
        1. Language: Traditional Chinese.
        2. Format:
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
        return f"連線錯誤：{str(e)}", "low", "動物", "動物醫院"

# --- 每日知識 ---
def get_daily_tip():
    if not GOOGLE_API_KEY: return "請設定 API Key 以啟用功能"
    try:
        genai.configure(api_key=GOOGLE_API_KEY)
        model = genai.GenerativeModel('gemini-2.5-flash')
        res = model.generate_content("給一個關於特殊寵物(爬蟲/鳥/兔)的有趣冷知識，50字內，繁體中文，開頭加上emoji")
        return res.text
    except:
        return "🐢 陸龜其實很喜歡曬太陽喔！"

# ====================
# 🖥️ 介面主程式
# ====================

st.markdown("""
    <div class="hero-container">
        <div class="hero-title">🐾 PetMatch AI智慧寵心導航🧑🏻‍⚕️</div>
        <div class="hero-subtitle">專為 🐱貓・🐶狗・🐢特寵 設計的AI醫療導航</div>
    </div>
""", unsafe_allow_html=True)

tab_home, tab_news, tab_about = st.tabs(["🏥 智能導航", "📰 衛教專區", "ℹ️ 關於我們"])

# --- TAB 1: 智能導航 ---
with tab_home:
    col_main, col_side = st.columns([2, 1])
    
    # 預設位置 (楠梓)
    default_pos = {"lat": 22.7268, "lon": 120.2975}
    current_user_pos = default_pos
    location_mode = "預設"

    with col_side:
        with st.container():
            st.markdown("### 📍 設定您的位置")
            
            # GPS 按鈕
            gps_location = get_geolocation(component_key='get_loc', button_text='📍 使用我的位置 (GPS)')
            
            # 手動選單
            manual_city = st.selectbox(
                "或手動選擇區域：",
                ["高雄市 (楠梓區)", "高雄市 (左營區)", "台北市 (信義區)", "台中市 (西屯區)"]
            )
            
            if gps_location and gps_location.get('coords'):
                current_user_pos = {
                    "lat": gps_location['coords']['latitude'],
                    "lon": gps_location['coords']['longitude']
                }
                location_mode = "GPS定位"
                st.success("✅ 定位成功！")
            else:
                user_coords = {
                    "高雄市 (楠梓區)": {"lat": 22.7268, "lon": 120.2975},
                    "高雄市 (左營區)": {"lat": 22.6800, "lon": 120.3000},
                    "台北市 (信義區)": {"lat": 25.0330, "lon": 121.5654},
                    "台中市 (西屯區)": {"lat": 24.1630, "lon": 120.6400}
                }
                current_user_pos = user_coords[manual_city]
                location_mode = manual_city

            st.info(f"目前位置：**{location_mode}**")
            st.caption(f"資料庫醫院數：{len(HOSPITALS_DB)} 家")
            
            if not GOOGLE_API_KEY:
                st.error("⚠️ 未偵測到 API Key")
            else:
                st.success("✅ AI 系統已連線")
            
    with col_main:
        if "messages" not in st.session_state:
            st.session_state.messages = [{"role": "assistant", "content": "嗨！我是 AI 醫療助理。請告訴我您的寵物怎麼了？"}]

        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])

        if prompt := st.chat_input("輸入症狀 (例如：守宮不吃東西)..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            st.chat_message("user").write(prompt)

            with st.chat_message("assistant"):
                with st.spinner("🧠 AI 正在分析並搜尋附近資源..."):
                    reply_text, urgency_level, animal_type, search_keywords = get_gemini_response(prompt)
                    st.write(reply_text)
                    st.session_state.messages.append({"role": "assistant", "content": reply_text})
                    
                    vip_hospitals = []
                    
                    if HOSPITALS_DB:
                        for h in HOSPITALS_DB:
                            # 1. 計算距離
                            dist = calculate_distance(current_user_pos['lat'], current_user_pos['lon'], h['lat'], h['lon'])
                            h['distance_km'] = round(dist, 1)
                            
                            tags_str = str(h['tags'])
                            
                            # 2. 判斷科別匹配
                            is_match = False
                            if animal_type in tags_str or any(k in tags_str for k in search_keywords.split()):
                                is_match = True
                            if urgency_level == "high" and ("24H" in tags_str or "急診" in tags_str):
                                is_match = True
                            
                            # 3. 嚴格篩選：只顯示 10 公里內 且 符合科別 的醫院
                            if is_match and dist < 10.0: 
                                vip_hospitals.append(h)

                    # 排序：由近到遠
                    vip_hospitals.sort(key=lambda x: x['distance_km'])

                    st.markdown("---")
                    
                    if urgency_level == "high":
                        st.error(f"🚨 高度緊急！AI 建議搜尋：{search_keywords}")
                    else:
                        st.info(f"ℹ️ 醫療建議類別：{animal_type}")

                    # --- 地圖顯示 ---
                    m = folium.Map(location=[current_user_pos["lat"], current_user_pos["lon"]], zoom_start=14)
                    folium.Marker([current_user_pos["lat"], current_user_pos["lon"]], icon=folium.Icon(color="blue", icon="user"), popup="您的位置").add_to(m)
                    
                    if vip_hospitals:
                        for h in vip_hospitals:
                            color = "red" if urgency_level == "high" else "green"
                            popup_info = f"<b>{h['name']}</b><br>距離: {h['distance_km']} km"
                            folium.Marker([h['lat'], h['lon']], popup=folium.Popup(popup_info, max_width=200), icon=folium.Icon(color=color, icon="plus")).add_to(m)
                    
                    components.html(m._repr_html_(), height=350)

                    # --- 醫院卡片 (顯示距離) ---
                    if vip_hospitals:
                        st.subheader(f"🏆 10公里內推薦 ({len(vip_hospitals)} 家)")
                        for h in vip_hospitals:
                            with st.container():
                                c1, c2 = st.columns([3, 1])
                                with c1:
                                    st.markdown(f"### 🏅 {h['name']}")
                                    st.markdown(f"**距離：{h['distance_km']} 公里** | ⭐ {h['rating']} | {h['status']}")
                                    tags_html = "".join([f"<span style='background:#E9ECEF;padding:2px 8px;border-radius:10px;margin-right:5px;font-size:0.8em'>#{t.strip()}</span>" for t in h['tags']])
                                    st.markdown(tags_html, unsafe_allow_html=True)
                                with c2:
                                    st.write("")
                                    link = f"https://www.google.com/maps/dir/?api=1&destination={h['lat']},{h['lon']}"
                                    st.link_button("🚗 導航", link, type="primary")
                            st.write("")
                    else:
                        # 這是最重要的修改：如果 10 公里內沒有，會明確告知
                        st.warning(f"⚠️ 在您附近 10 公里內，暫無資料庫認證的 **{animal_type}** 醫院。")
                        st.caption("建議您擴大搜尋範圍，或點擊下方按鈕使用 Google Maps 查詢。")

                    st.markdown("#### 沒找到合適的？")
                    # 使用 GPS 座標進行 Google Maps 搜尋
                    gmap_query = f"http://googleusercontent.com/maps.google.com/maps?q={search_keywords}&center={current_user_pos['lat']},{current_user_pos['lon']}"
                    st.link_button(f"🔍 搜尋附近的「{search_keywords}」", gmap_query, type="secondary")

# --- TAB 2: 衛教專區 ---
with tab_news:
    st.markdown("""
    <div style="background-color:#E3F2FD;padding:20px;border-radius:10px;border-left:5px solid #2196F3;">
        <h4>✨ AI 每日冷知識</h4>
    </div>
    """, unsafe_allow_html=True)
    
    if "daily_tip" not in st.session_state:
        st.session_state.daily_tip = get_daily_tip()
    
    st.write(f"💡 {st.session_state.daily_tip}")
    if st.button("🔄 換一則"):
        st.session_state.daily_tip = get_daily_tip()
        st.rerun()
    
    st.divider()
    
    st.subheader("📌 熱門文章")
    ac1, ac2 = st.columns(2)
    
    with ac1:
        with st.container():
            st.image("https://images.unsplash.com/photo-1550949752-64157d6051eb?q=80&w=400")
            st.markdown("#### 🐢 陸龜過冬三大重點")
            st.caption("#爬蟲 #保溫")
            st.write("冬天是爬蟲類的殺手。別讓你的陸龜感冒了，這些保溫設備你都有了嗎？")
            st.button("閱讀全文", key="b1")
            
    with ac2:
        with st.container():
            st.image("https://images.unsplash.com/photo-1585110396065-88b74662ee2a?q=80&w=400")
            st.markdown("#### 🐇 兔子不吃草怎麼辦？")
            st.caption("#哺乳 #腸胃")
            st.write("兔子 24 小時不吃草就有生命危險！學會判斷腸胃停滯的早期徵兆。")
            st.button("閱讀全文", key="b2")

# --- TAB 3: 關於 ---
with tab_about:
    st.markdown("""
    ### 關於 PetMatch
    我們致力於解決特殊寵物就醫資訊不透明的問題。
    """)
    st.image("https://images.unsplash.com/photo-1548767797-d8c844163c4c?q=80&w=800")