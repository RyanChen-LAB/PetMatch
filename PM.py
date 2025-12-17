import streamlit as st
import pandas as pd
import google.generativeai as genai
import folium
import streamlit.components.v1 as components
from streamlit_js_eval import get_geolocation 
from math import radians, cos, sin, asin, sqrt
import time

# --- 1. 頁面設定 ---
st.set_page_config(
    page_title="PetMatch AI智慧寵心導航", 
    page_icon="🐾", 
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={'Get Help': None, 'Report a bug': None, 'About': None}
)

# ====== 🎨 CSS 介面終極修復 + 🛡️ Aggressive Hiding (v31.0) ======
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;700&family=Nunito:wght@700&display=swap');
    
    :root { --primary-color: #2A9D8F; --background-color: #F9F7F2; --text-color: #264653; --font: "Noto Sans TC", sans-serif; }
    html, body, [class*="css"], .stApp { font-family: 'Noto Sans TC', sans-serif; color: #264653 !important; background-color: #F9F7F2 !important; }
    
    /* 隱藏選單 */
    header, [data-testid="stToolbar"], .stAppDeployButton, [data-testid="stHeader"], .viewerBadge_container__1QSob, footer { display: none !important; visibility: hidden !important; }
    .block-container { padding-top: 1rem !important; }

    /* 文字與按鈕 */
    .stMarkdown p, h1, h2, h3, h4, h5, h6, .stText, .stHtml, .stCaption { color: #264653 !important; }
    .stButton > button[kind="primary"] { background: linear-gradient(to bottom, #2A9D8F, #21867a) !important; color: white !important; border: none; border-radius: 15px; padding: 18px 24px; width: 100%; box-shadow: 0 6px 0 #1A6B63; margin-bottom: 15px; }
    .stButton > button[kind="primary"]:active { transform: translateY(6px); box-shadow: 0 0 0 #1A6B63; }
    .stLinkButton > a[kind="secondary"] { background: linear-gradient(to bottom, #E76F51, #D65A3F) !important; color: white !important; border-radius: 15px; padding: 18px 24px; width: 100%; text-align: center; display: block; box-shadow: 0 6px 0 #A83E26; margin-top: 10px; }
    .stLinkButton > a[kind="secondary"]:active { transform: translateY(6px); box-shadow: 0 0 0 #A83E26; }
    .stButton > button p, .stLinkButton > a { color: white !important; }
    
    /* 其他 UI */
    .hero-container { background: linear-gradient(120deg, #e0f7fa 0%, #b2dfdb 100%); padding: 30px; border-radius: 20px; text-align: center; margin-bottom: 25px; border: 2px solid #2A9D8F; }
    .hero-title { font-family: 'Nunito', sans-serif; font-size: 2.2rem; font-weight: 800; margin: 0; color: #264653 !important; }
    .hero-subtitle { font-size: 1.1rem; margin-top: 8px; font-weight: 700; color: #2A9D8F !important; }
    div[data-testid="stAlert"] p { color: #000000 !important; font-weight: 500; }
    .stat-box small { color: #666 !important; } .stat-box b { color: #2A9D8F !important; }
</style>
""", unsafe_allow_html=True)

# ====== 🔑 API KEY Configuration ======
try:
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
except:
    GOOGLE_API_KEY = "" 

# --- Utility ---
def calculate_distance(lat1, lon1, lat2, lon2):
    try:
        lon1, lat1, lon2, lat2 = map(radians, [float(lon1), float(lat1), float(lon2), float(lat2)])
        dlon = lon2 - lon1 
        dlat = lat2 - lat1 
        part1 = sin(dlat/2)**2
        part2 = cos(lat1) * cos(lat2) * sin(dlon/2)**2
        a = part1 + part2
        c = 2 * asin(sqrt(a)) 
        r = 6371 
        return c * r
    except:
        return 9999

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

# --- 🔥 新增：AI 連線檢測函式 (只測綠燈模型) ---
def check_api_connection():
    if not GOOGLE_API_KEY: return None
    
    # 🔥 關鍵修正：只使用您檢測報告中的「綠燈」模型
    test_models = [
        'gemini-2.5-flash-lite',      # 首選：最新 Lite
        'gemini-flash-lite-latest',   # 備用：通用 Lite
        'gemma-3-4b-it'               # 保底：Gemma (不同額度池)
    ]
    
    genai.configure(api_key=GOOGLE_API_KEY)
    
    for model_name in test_models:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content("Hi")
            if response and response.text:
                return model_name
        except:
            time.sleep(0.2)
            continue 
            
    return None

# --- AI Core (🔥 v31.0: 綠燈通道) ---
def get_gemini_response(user_input):
    if not GOOGLE_API_KEY:
        return "⚠️ 請檢查 API Key", "low", "動物", "動物醫院"
    
    active_model = st.session_state.get('active_model_name', None)
    
    if not active_model:
        models_to_try = [
            'gemini-2.5-flash-lite', 
            'gemini-flash-lite-latest',
            'gemma-3-4b-it'
        ]
    else:
        models_to_try = [active_model, 'gemma-3-4b-it']

    system_prompt = f"""
    Role: PetMatch Triage System. Task: Analyze input: "{user_input}"
    Rules: Traditional Chinese. Format:
    URGENCY: [HIGH/MEDIUM/LOW]
    RESPONSE: [Advice within 100 words.]
    ANIMAL_TYPE: [e.g., 爬蟲, 鳥類, 兔子]
    SEARCH_KEYWORDS: [e.g., 爬蟲 動物醫院, 24H 急診]
    """

    for model_name in models_to_try:
        try:
            genai.configure(api_key=GOOGLE_API_KEY)
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(system_prompt)
            
            if not response.text: raise ValueError("Empty")
            text = response.text
            
            st.session_state['active_model_name'] = model_name
            st.session_state['connection_status'] = "connected"
            
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
            print(f"Error {model_name}: {e}")
            time.sleep(1)
            continue

    return "⚠️ 系統目前繁忙，請直接參考下方推薦醫院。", "high", "動物", "24H 動物醫院"

# --- Daily Tip (🔥 v31.0: 用 Gemma 最省) ---
def get_daily_tip():
    if not GOOGLE_API_KEY: return "請設定 API Key"
    try:
        genai.configure(api_key=GOOGLE_API_KEY)
        # 使用超輕量 Gemma，完全不佔用 Gemini 額度
        model = genai.GenerativeModel('gemma-3-1b-it') 
        res = model.generate_content("給一個關於特殊寵物(爬蟲/鳥/兔)的有趣冷知識，50字內，繁體中文，開頭加上emoji")
        return res.text
    except:
        return "🐢 陸龜其實很喜歡曬太陽喔！"

# ====================
# 🖥️ Main Interface
# ====================

# 1. Hero Header
st.markdown("""
    <div class="hero-container">
        <div class="hero-title">👨🏻‍⚕️ PetMatch AI智慧寵心導航</div>
        <div class="hero-subtitle">專為 🐱貓・🐶狗・🐢特寵 設計的AI醫療導航</div>
    </div>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown("### ℹ️ 系統狀態")
    
    if not GOOGLE_API_KEY:
        st.error("⚠️ 未偵測到 API Key")
    else:
        # 自動檢測
        if 'connection_status' not in st.session_state:
            with st.spinner("正在切換可用線路..."):
                connected_model = check_api_connection()
                
            if connected_model:
                st.session_state['connection_status'] = "connected"
                st.session_state['active_model_name'] = connected_model
            else:
                st.session_state['connection_status'] = "failed"
                st.session_state['active_model_name'] = None

        if st.session_state['connection_status'] == "connected":
            status_html = f"""
            <div class="stat-box" style="text-align:center; padding:15px; background:#E8F5E9; border-radius:10px; border: 2px solid #2A9D8F;">
                <b style="color:#2A9D8F; font-size: 1.2rem;">✅ AI 連線正常</b><br>
                <hr style="margin: 8px 0; border-color: #A5D6A7;">
                <small style="color:#555;">使用模型：</small><br>
                <code style="color:#1B5E20; font-weight:bold; font-size: 0.9rem;">{st.session_state['active_model_name']}</code>
                <br><br>
                <small style="color:#555;">已收錄醫院：</small> 
                <b style="color:#2A9D8F;">{len(HOSPITALS_DB)}</b> <small>家</small>
            </div>
            """
        else:
            status_html = f"""
            <div class="stat-box" style="text-align:center; padding:15px; background:#FFEBEE; border-radius:10px; border: 2px solid #EF5350;">
                <b style="color:#C62828; font-size: 1.2rem;">❌ 連線不穩</b><br>
                <small style="color:#666;">正在嘗試切換備用線路</small>
                <br><br>
                <small style="color:#555;">已收錄醫院：</small> 
                <b style="color:#2A9D8F;">{len(HOSPITALS_DB)}</b> <small>家</small>
            </div>
            """

    st.markdown(status_html, unsafe_allow_html=True)
    
    if GOOGLE_API_KEY and st.session_state.get('connection_status') == "failed":
        if st.button("🔄 強制切換線路", type="primary"):
            del st.session_state['connection_status']
            st.rerun()
            
    st.caption("v31.0 綠燈通道版")

# Tabs
tab_home, tab_news, tab_about = st.tabs(["🏥 智能導航", "📰 衛教專區", "ℹ️ 關於我們"])

# --- TAB 1: Smart Navigation ---
with tab_home:
    if 'current_pos' not in st.session_state:
        st.session_state.current_pos = {"lat": 22.7268, "lon": 120.2975}
        st.session_state.location_name = "高雄市 (楠梓區)"

    # Location Section
    with st.container(border=True):
        st.markdown('<div class="step-header">📍 第一步：確認您的位置</div>', unsafe_allow_html=True)
        col_gps_btn, col_map_view = st.columns([1, 2])
        
        with col_gps_btn:
            if 'gps_activated' not in st.session_state: st.session_state.gps_activated = False
            if st.button("📍 點擊啟用定位系統", type="primary", use_container_width=True):
                st.session_state.gps_activated = True
                st.rerun()

            if st.session_state.gps_activated:
                gps_location = get_geolocation(component_key='get_loc')
                if gps_location and gps_location.get('coords'):
                    st.session_state.current_pos = {"lat": gps_location['coords']['latitude'], "lon": gps_location['coords']['longitude']}
                    st.success("✅ 已定位成功！")
            
            with st.expander("🔧 手動切換行政區"):
                kaohsiung_coords = {
                    "楠梓區": {"lat": 22.7268, "lon": 120.2975}, "左營區": {"lat": 22.6800, "lon": 120.3000},
                    "三民區": {"lat": 22.6496, "lon": 120.3292}, "鼓山區": {"lat": 22.6368, "lon": 120.2795},
                    "苓雅區": {"lat": 22.6204, "lon": 120.3123}, "新興區": {"lat": 22.6293, "lon": 120.3023},
                    "前金區": {"lat": 22.6277, "lon": 120.2936}, "鹽埕區": {"lat": 22.6247, "lon": 120.2835},
                    "前鎮區": {"lat": 22.5864, "lon": 120.3180}, "旗津區": {"lat": 22.5694, "lon": 120.2778},
                    "小港區": {"lat": 22.5656, "lon": 120.3542}, "鳳山區": {"lat": 22.6269, "lon": 120.3574}
                }
                manual_area = st.selectbox("👇 選擇區域：", list(kaohsiung_coords.keys()))
                if st.button("確認切換", type="primary"):
                    st.session_state.current_pos = kaohsiung_coords[manual_area]
                    st.rerun()

        with col_map_view:
            m_preview = folium.Map(location=[st.session_state.current_pos["lat"], st.session_state.current_pos["lon"]], zoom_start=14)
            folium.Marker([st.session_state.current_pos["lat"], st.session_state.current_pos["lon"]], icon=folium.Icon(color="blue", icon="user"), popup="您的位置").add_to(m_preview)
            if HOSPITALS_DB:
                for h in HOSPITALS_DB:
                    folium.CircleMarker(location=[h['lat'], h['lon']], radius=5, color="green", fill=True, fill_opacity=0.6, tooltip=h['name']).add_to(m_preview)
            components.html(m_preview._repr_html_(), height=250)

    # AI Section
    st.write("") 
    with st.container(border=True):
        st.markdown('<div class="step-header">💬 第二步：AI 醫療諮詢</div>', unsafe_allow_html=True)
        if "messages" not in st.session_state: st.session_state.messages = [{"role": "assistant", "content": "嗨！我是 AI 醫療助理。請告訴我您的寵物怎麼了？"}]
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]): st.write(msg["content"])

        if prompt := st.chat_input("輸入症狀..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            st.chat_message("user").write(prompt)
            with st.chat_message("assistant"):
                with st.spinner("🧠 分析中..."):
                    reply_text, urgency, animal_type, keywords = get_gemini_response(prompt)
                    st.write(reply_text)
                    st.session_state.messages.append({"role": "assistant", "content": reply_text})
                    
                    vip_hospitals = []
                    if HOSPITALS_DB:
                        for h in HOSPITALS_DB:
                            h['distance_km'] = round(calculate_distance(st.session_state.current_pos['lat'], st.session_state.current_pos['lon'], h['lat'], h['lon']), 1)
                            is_match = False
                            tags = str(h['tags'])
                            if animal_type in tags or any(k in tags for k in keywords.split()): is_match = True
                            if urgency == "high" and ("24H" in tags or "急診" in tags): is_match = True
                            if is_match: vip_hospitals.append(h)
                    
                    vip_hospitals.sort(key=lambda x: x['distance_km'])
                    display_hospitals = vip_hospitals[:5]

                    st.markdown("---")
                    if urgency == "high": st.error(f"🚨 緊急建議：{keywords}")
                    else: st.info(f"ℹ️ 類別：{animal_type}")

                    if display_hospitals:
                        st.subheader("🏆 推薦醫院")
                        for h in display_hospitals:
                            with st.container():
                                c1, c2 = st.columns([3, 1])
                                with c1:
                                    st.markdown(f"**{h['name']}** ({h['distance_km']}km)\n⭐{h['rating']} | {h['status']}")
                                with c2:
                                    st.link_button("🚗 導航", f"https://www.google.com/maps/dir/?api=1&destination={h['lat']},{h['lon']}", type="primary")
                    else:
                        st.warning("⚠️ 附近無匹配醫院")
                        
                    st.link_button(f"🔍 Google Maps 搜尋", f"https://www.google.com/maps/search/?api=1&query={keywords}", type="secondary", use_container_width=True)

# --- TAB 2 & 3 ---
with tab_news:
    if "daily_tip" not in st.session_state: st.session_state.daily_tip = get_daily_tip()
    st.info(f"💡 冷知識：{st.session_state.daily_tip}")
with tab_about:
    st.markdown("### 關於 PetMatch\n專為特寵設計的 AI 醫療導航。")
