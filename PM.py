import streamlit as st
import pandas as pd
import google.generativeai as genai
import folium
import streamlit.components.v1 as components
from streamlit_js_eval import get_geolocation 
from math import radians, cos, sin, asin, sqrt

# --- 1. 頁面設定 ---
st.set_page_config(page_title="PetMatch AI智慧寵心導航", page_icon="🐾", layout="wide")

# ====== 🎨 CSS 極致美化魔法區 (v3.0 Pro) ======
st.markdown("""
<style>
    /* 引入現代字體 */
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@300;500;700&family=Nunito:wght@700&display=swap');
    
    /* 全域設定 */
    html, body, [class*="css"] {
        font-family: 'Noto Sans TC', sans-serif;
    }
    
    /* 背景色：溫暖的奶油白，護眼且高級 */
    .stApp {
        background-color: #F9F7F2; 
    }

    /* --- 頂部 Hero Header --- */
    .hero-box {
        background: linear-gradient(120deg, #264653, #2A9D8F);
        padding: 40px;
        border-radius: 20px;
        color: white;
        text-align: center;
        box-shadow: 0 10px 20px rgba(42, 157, 143, 0.2);
        margin-bottom: 30px;
        position: relative;
        overflow: hidden;
    }
    .hero-title {
        font-family: 'Nunito', sans-serif;
        font-size: 3rem;
        font-weight: 800;
        margin: 0;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
    }
    .hero-subtitle {
        font-size: 1.1rem;
        opacity: 0.9;
        margin-top: 10px;
        font-weight: 300;
        letter-spacing: 1px;
    }

    /* --- 側邊欄定位按鈕 (3D 黃金按鈕) --- */
    /* 針對側邊欄的第一個按鈕進行特殊樣式設計 */
    section[data-testid="stSidebar"] .stButton button {
        background: linear-gradient(to bottom, #F4A261, #E76F51);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 18px 24px;
        font-weight: 700;
        font-size: 1.1rem;
        box-shadow: 0 6px 0 #C0583E, 0 12px 10px rgba(0,0,0,0.2);
        transition: all 0.1s;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 20px;
    }
    section[data-testid="stSidebar"] .stButton button:hover {
        background: linear-gradient(to bottom, #F5B076, #EC8368);
        transform: translateY(-2px);
        box-shadow: 0 8px 0 #C0583E, 0 15px 20px rgba(0,0,0,0.2);
    }
    section[data-testid="stSidebar"] .stButton button:active {
        transform: translateY(4px);
        box-shadow: 0 2px 0 #C0583E, 0 2px 2px rgba(0,0,0,0.1);
    }

    /* --- 醫院卡片 (懸浮效果) --- */
    div[data-testid="stVerticalBlock"] > div[style*="background-color"] {
        background-color: white !important;
        border-radius: 20px;
        padding: 25px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        border: 1px solid #F0F0F0;
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }
    div[data-testid="stVerticalBlock"] > div[style*="background-color"]:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 25px rgba(0,0,0,0.1);
        border-color: #2A9D8F;
    }

    /* --- 標籤膠囊 (Pills) --- */
    .tag-pill {
        display: inline-block;
        background-color: #E8F5E9;
        color: #2E7D32;
        padding: 4px 12px;
        border-radius: 50px;
        font-size: 0.85rem;
        font-weight: 500;
        margin-right: 6px;
        margin-bottom: 6px;
        border: 1px solid #C8E6C9;
    }
    .tag-pill.emergency {
        background-color: #FFEBEE;
        color: #C62828;
        border-color: #FFCDD2;
    }

    /* --- 聊天氣泡優化 --- */
    .stChatMessage {
        background-color: white;
        border-radius: 18px;
        padding: 15px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        margin-bottom: 10px;
        border: 1px solid #F1F1F1;
    }
    .stChatMessage[data-testid="stChatMessage"]:nth-child(odd) {
        background-color: #E0F2F1; /* 助理的氣泡帶點綠 */
    }

    /* --- 一般按鈕 (導航用) --- */
    .element-container .stButton > button {
        border-radius: 50px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# ====== 🔑 API KEY 設定區 ======
try:
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
except:
    GOOGLE_API_KEY = "" 
# ==============================

# --- 工具：計算距離 ---
def calculate_distance(lat1, lon1, lat2, lon2):
    try:
        lon1, lat1, lon2, lat2 = map(radians, [float(lon1), float(lat1), float(lon2), float(lat2)])
        dlon = lon2 - lon1 
        dlat = lat2 - lat1 
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a)) 
        r = 6371 
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
        return "⚠️ 請檢查 API Key", "low", "動物", "動物醫院"
    
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

# 1. 華麗的 Hero Header
st.markdown("""
    <div class="hero-box">
         <div class="hero-title">🐾 PetMatch AI智慧寵心導航🧑🏻‍⚕️</div>
        <div class="hero-subtitle">專為 🐱貓・🐶狗・🐢特寵 設計的AI醫療導航</div>
    </div>
""", unsafe_allow_html=True)

tab_home, tab_news, tab_about = st.tabs(["🏥 智能導航", "📰 衛教專區", "ℹ️ 關於我們"])

# --- TAB 1: 智能導航 ---
with tab_home:
    col_main, col_side = st.columns([2, 1])
    
    # 預設位置：高雄市楠梓區
    default_pos = {"lat": 22.7268, "lon": 120.2975}
    current_user_pos = default_pos
    location_status = "使用預設位置 (楠梓)"

    with col_side:
        # 側邊欄容器
        with st.container():
            st.markdown("### 📍 您的位置")
            
            # 🚀 3D 立體按鈕開關
            use_gps = st.checkbox("📍 使用我的位置 (GPS Mode)")
            
            if use_gps:
                gps_location = get_geolocation(component_key='get_loc')
                
                if gps_location and gps_location.get('coords'):
                    current_user_pos = {
                        "lat": gps_location['coords']['latitude'],
                        "lon": gps_location['coords']['longitude']
                    }
                    st.success("✅ 已完成您的定位")
                else:
                    st.info("📡 正在衛星連線中... 請允許瀏覽器權限")
            else:
                st.info("📌 目前使用預設位置：高雄市 (楠梓)")

            st.markdown("---")
            
            # 統計資訊小卡
            st.markdown(f"""
            <div style="text-align:center; padding:10px; background:#EFEFEF; border-radius:10px;">
                <small>目前資料庫收錄</small><br>
                <b style="font-size:1.5rem; color:#2A9D8F;">{len(HOSPITALS_DB)}</b> <small>家專科醫院</small>
            </div>
            """, unsafe_allow_html=True)
            
            if not GOOGLE_API_KEY:
                st.error("⚠️ 未偵測到 API Key")
            
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
                            dist = calculate_distance(current_user_pos['lat'], current_user_pos['lon'], h['lat'], h['lon'])
                            h['distance_km'] = round(dist, 1)
                            
                            tags_str = str(h['tags'])
                            
                            is_match = False
                            if animal_type in tags_str or any(k in tags_str for k in search_keywords.split()):
                                is_match = True
                            if urgency_level == "high" and ("24H" in tags_str or "急診" in tags_str):
                                is_match = True
                            
                            # 10 公里篩選
                            if is_match and dist < 10.0: 
                                vip_hospitals.append(h)

                    vip_hospitals.sort(key=lambda x: x['distance_km'])

                    st.markdown("---")
                    
                    if urgency_level == "high":
                        st.error(f"🚨 高度緊急！AI 建議搜尋：{search_keywords}")
                    else:
                        st.info(f"ℹ️ 醫療建議類別：{animal_type}")

                    m = folium.Map(location=[current_user_pos["lat"], current_user_pos["lon"]], zoom_start=14)
                    folium.Marker([current_user_pos["lat"], current_user_pos["lon"]], icon=folium.Icon(color="blue", icon="user"), popup="您的位置").add_to(m)
                    
                    if vip_hospitals:
                        for h in vip_hospitals:
                            color = "red" if urgency_level == "high" else "green"
                            popup_info = f"<b>{h['name']}</b><br>距離: {h['distance_km']} km"
                            folium.Marker([h['lat'], h['lon']], popup=folium.Popup(popup_info, max_width=200), icon=folium.Icon(color=color, icon="plus")).add_to(m)
                    
                    components.html(m._repr_html_(), height=350)

                    # --- 醫院卡片 (美化版) ---
                    if vip_hospitals:
                        st.subheader(f"🏆 10公里內推薦 ({len(vip_hospitals)} 家)")
                        for h in vip_hospitals:
                            with st.container():
                                c1, c2 = st.columns([3, 1])
                                with c1:
                                    st.markdown(f"### 🏅 {h['name']}")
                                    st.markdown(f"**距離：{h['distance_km']} 公里** | ⭐ {h['rating']} | {h['status']}")
                                    
                                    # 標籤膠囊化 (Pills)
                                    tags_html = ""
                                    for t in h['tags']:
                                        t_clean = t.strip()
                                        if "24H" in t_clean or "急診" in t_clean:
                                            tags_html += f'<span class="tag-pill emergency">{t_clean}</span>'
                                        else:
                                            tags_html += f'<span class="tag-pill">{t_clean}</span>'
                                    st.markdown(tags_html, unsafe_allow_html=True)
                                    
                                with c2:
                                    st.write("")
                                    link = f"https://www.google.com/maps/dir/?api=1&destination={h['lat']},{h['lon']}"
                                    st.link_button("🚗 導航", link, type="primary")
                            st.write("") # 卡片間距
                    else:
                        st.warning(f"⚠️ 在您附近 10 公里內，暫無資料庫認證的 **{animal_type}** 醫院。")
                        st.caption("建議您擴大搜尋範圍，或點擊下方按鈕使用 Google Maps 查詢。")

                    st.markdown("#### 沒找到合適的？")
                    gmap_query = f"http://googleusercontent.com/maps.google.com/maps?q={search_keywords}&center={current_user_pos['lat']},{current_user_pos['lon']}"
                    st.link_button(f"🔍 搜尋附近的「{search_keywords}」", gmap_query, type="secondary")

# --- TAB 2: 衛教專區 ---
with tab_news:
    st.markdown("""
    <div style="background-color:#E3F2FD;padding:20px;border-radius:15px;border-left:6px solid #2196F3; box-shadow:0 2px 5px rgba(0,0,0,0.05);">
        <h4 style="margin:0;color:#1565C0;">✨ AI 每日冷知識</h4>
    </div>
    """, unsafe_allow_html=True)
    
    if "daily_tip" not in st.session_state:
        st.session_state.daily_tip = get_daily_tip()
    
    st.markdown(f"<div style='padding:15px; font-size:1.1rem;'>💡 {st.session_state.daily_tip}</div>", unsafe_allow_html=True)
    
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