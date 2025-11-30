import streamlit as st
import pandas as pd
import google.generativeai as genai
import folium
import streamlit.components.v1 as components

# --- 1. 頁面設定 ---
st.set_page_config(page_title="PetMatch AI智慧寵心導航", page_icon="🐾", layout="wide")

# ====== 🎨 CSS 美化魔法區 ======
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Noto Sans TC', sans-serif; }
    .stApp { background-color: #F8F9FA; }
    
    /* 頂部 Hero Section */
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

    /* 卡片樣式 */
    div[data-testid="stVerticalBlock"] > div[style*="background-color"] {
        background-color: white !important;
        border-radius: 15px;
        padding: 20px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        border: 1px solid #E0E0E0;
    }
    
    /* 按鈕美化 */
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
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }
    
    /* 聊天框美化 */
    .stChatMessage {
        background-color: #ffffff;
        border-radius: 15px;
        padding: 10px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)

# ====== 🔑 API KEY 設定區 (GitHub 安全版) ======
# 這裡不需要填寫 Key！程式會自動去讀取 Streamlit Cloud 的設定
try:
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
except:
    # 只有在本機電腦跑，且沒有 secrets.toml 時，這裡才需要暫時填寫
    # 上傳 GitHub 前請確保這裡是空的或註解掉
    GOOGLE_API_KEY = "" 
# ============================================

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
        return "⚠️ 請檢查 API Key 設定 (Streamlit Secrets)", "low", "動物", "動物醫院"
    
    try:
        genai.configure(api_key=GOOGLE_API_KEY)
        model = genai.GenerativeModel('gemini-2.0-flash')
        
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
    except:
        return "連線錯誤 (請檢查 API Key 或額度)", "low", "動物", "動物醫院"

# --- 每日知識 ---
def get_daily_tip():
    if not GOOGLE_API_KEY: return "請設定 API Key 以啟用功能"
    try:
        genai.configure(api_key=GOOGLE_API_KEY)
        model = genai.GenerativeModel('gemini-2.0-flash')
        res = model.generate_content("給一個關於特殊寵物(爬蟲/鳥/兔)的有趣冷知識，50字內，繁體中文，開頭加上emoji")
        return res.text
    except:
        return "🐢 陸龜其實很喜歡曬太陽喔！"

# ====================
# 🖥️ 介面主程式
# ====================

# 1. 頂部 Hero Section
st.markdown("""
    <div class="hero-container">
        <div class="hero-title">🐾 PetMatch AI智慧寵心導航</div>
        <div class="hero-subtitle">專為 爬蟲・鳥類・特寵 設計的 AI 醫療導航</div>
    </div>
""", unsafe_allow_html=True)

# 2. 分頁導航
tab_home, tab_news, tab_about = st.tabs(["🏥 智能導航", "📰 衛教專區", "ℹ️ 關於我們"])

# --- TAB 1: 智能導航 ---
with tab_home:
    col_main, col_side = st.columns([2, 1])
    current_user_pos = {"lat": 22.6800, "lon": 120.3000} # 高雄市左營區
    
    with col_side:
        with st.container():
            st.markdown("### 📍 目前位置")
            st.info("高雄市 (預設)")
            st.caption(f"資料庫醫院數：{len(HOSPITALS_DB)} 家")
            st.markdown("---")
            if not GOOGLE_API_KEY:
                st.error("⚠️ 未偵測到 API Key，請至 Streamlit Cloud 設定 Secrets。")
            else:
                st.success("✅ AI 系統運作中")
            
    with col_main:
        if "messages" not in st.session_state:
            st.session_state.messages = [{"role": "assistant", "content": "嗨！我是 AI 醫療助理。高雄的朋友，請告訴我您的寵物怎麼了？"}]

        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])

        if prompt := st.chat_input("輸入症狀 (例如：守宮不吃東西)..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            st.chat_message("user").write(prompt)

            with st.chat_message("assistant"):
                with st.spinner("🧠 AI 正在分析..."):
                    reply_text, urgency_level, animal_type, search_keywords = get_gemini_response(prompt)
                    st.write(reply_text)
                    st.session_state.messages.append({"role": "assistant", "content": reply_text})
                    
                    vip_hospitals = []
                    if HOSPITALS_DB:
                        for h in HOSPITALS_DB:
                            tags_str = str(h['tags'])
                            if animal_type in tags_str or any(k in tags_str for k in search_keywords.split()):
                                vip_hospitals.append(h)
                            if urgency_level == "high" and ("24H" in tags_str or "急診" in tags_str):
                                if h not in vip_hospitals: vip_hospitals.append(h)

                    st.markdown("---")
                    
                    if urgency_level == "high":
                        st.error(f"🚨 高度緊急！AI 建議搜尋：{search_keywords}")
                    else:
                        st.info(f"ℹ️ 醫療建議類別：{animal_type}")

                    m = folium.Map(location=[current_user_pos["lat"], current_user_pos["lon"]], zoom_start=13)
                    folium.Marker([current_user_pos["lat"], current_user_pos["lon"]], icon=folium.Icon(color="blue", icon="user"), popup="您 (高雄)").add_to(m)
                    
                    if vip_hospitals:
                        h_color = "red" if urgency_level == "high" else "green"
                        for h in vip_hospitals:
                            popup_info = f"<b>{h['name']}</b><br>{h['phone']}"
                            folium.Marker([h['lat'], h['lon']], popup=folium.Popup(popup_info, max_width=200), icon=folium.Icon(color=h_color, icon="plus")).add_to(m)
                    
                    components.html(m._repr_html_(), height=350)

                    # --- 推薦醫院卡片 (修正連結) ---
                    if vip_hospitals:
                        st.subheader(f"🏆 推薦 {animal_type} 專科")
                        for h in vip_hospitals:
                            with st.container():
                                c1, c2 = st.columns([3, 1])
                                with c1:
                                    st.markdown(f"### 🏅 {h['name']}")
                                    st.markdown(f"**評價：** {h['rating']} ⭐ | **狀態：** {h['status']}")
                                    tags_html = "".join([f"<span style='background:#E9ECEF;padding:2px 8px;border-radius:10px;margin-right:5px;font-size:0.8em'>#{t.strip()}</span>" for t in h['tags']])
                                    st.markdown(tags_html, unsafe_allow_html=True)
                                with c2:
                                    st.write("")
                                    # ✅ 修正點：使用 Google Maps 官方標準導航連結
                                    link = f"https://www.google.com/maps/dir/?api=1&destination={h['lat']},{h['lon']}"
                                    st.link_button("🚗 導航", link, type="primary")
                            st.write("")

                    # 擴大搜尋按鈕 (修正連結)
                    st.markdown("#### 沒找到合適的？")
                    # ✅ 修正點：使用 Google Maps 官方標準搜尋連結
                    gmap_query = f"https://www.google.com/maps/search/?api=1&query={search_keywords}"
                    st.link_button(f"🔍 在 Google Maps 搜尋「{search_keywords}」", gmap_query, type="secondary")

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
    
    - **精準導航**：連結專科醫院資料庫。
    - **AI 分診**：減少飼主焦慮。
    - **社群共享**：最新的衛教資訊。
    """)
    st.image("https://images.unsplash.com/photo-1548767797-d8c844163c4c?q=80&w=800")