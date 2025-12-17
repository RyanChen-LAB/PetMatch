import streamlit as st
import pandas as pd
import google.generativeai as genai
import folium
import streamlit.components.v1 as components
from streamlit_js_eval import get_geolocation 
from math import radians, cos, sin, asin, sqrt
import time # ✅ 新增：用於連線重試的計時器

# --- 1. 頁面設定 ---
st.set_page_config(page_title="PetMatch AI智慧寵心導航", page_icon="🐾", layout="wide")

# ====== 🎨 CSS 介面終極修復 (基於 v10.2 優化) ======
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;700&family=Nunito:wght@700&display=swap');
    
    /* 1. 強制定義淺色主題變數 */
    :root {
        --primary-color: #2A9D8F;
        --background-color: #F9F7F2;
        --secondary-background-color: #F0F2F6;
        --text-color: #264653;
        --font: "Noto Sans TC", sans-serif;
    }

    /* 2. 強制全域背景與文字顏色 */
    html, body, [class*="css"], .stApp {
        font-family: 'Noto Sans TC', sans-serif;
        color: #264653 !important;
        background-color: #F9F7F2 !important;
    }

    /* 3. 強制通用文字顯色 */
    .stMarkdown p, .stMarkdown span, .stMarkdown div, 
    h1, h2, h3, h4, h5, h6, 
    .stText, .stHtml, .stCaption {
        color: #264653 !important;
    }

    /* 4. Toggle 開關與 Checkbox 文字 */
    label[data-testid="stWidgetLabel"] p {
        color: #264653 !important;
        font-weight: 700;
        font-size: 1.1rem;
    }
    
    /* 5. 提示框 (Success/Warning) 文字 */
    div[data-testid="stAlert"] p, div[data-testid="stAlert"] div {
        color: #000000 !important; 
        font-weight: 500;
    }

    /* 6. 摺疊選單標題 */
    .streamlit-expanderHeader p {
        color: #264653 !important;
        font-weight: 600;
    }

    /* 7. 分頁標籤文字 */
    button[data-baseweb="tab"] div p {
        color: #264653 !important;
        font-weight: 700 !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        border-bottom-color: #2A9D8F !important;
    }

    /* 8. Hero Header */
    .hero-container {
        background: linear-gradient(120deg, #e0f7fa 0%, #b2dfdb 100%);
        padding: 30px;
        border-radius: 20px;
        text-align: center;
        box-shadow: 0 10px 20px rgba(42, 157, 143, 0.1);
        margin-bottom: 25px;
        border: 2px solid #2A9D8F;
    }
    .hero-title { 
        font-family: 'Nunito', sans-serif; 
        font-size: 2.2rem; 
        font-weight: 800; 
        margin: 0; 
        color: #264653 !important; 
        text-shadow: none;
    }
    .hero-subtitle { 
        font-size: 1.1rem; 
        opacity: 1; 
        margin-top: 8px; 
        font-weight: 700; 
        color: #2A9D8F !important; 
        letter-spacing: 1px; 
    }

    /* 9. 3D 按鈕樣式 */
    .stButton > button[kind="primary"] {
        background: linear-gradient(to bottom, #2A9D8F, #21867a) !important;
        color: white !important;
        border: none;
        border-radius: 15px;
        padding: 18px 24px;
        font-size: 1.2rem !important;
        font-weight: 900 !important;
        width: 100%;
        box-shadow: 0 6px 0 #1A6B63, 0 12px 15px rgba(0,0,0,0.2);
        transition: all 0.1s ease;
        margin-bottom: 15px;
    }
    .stButton > button[kind="primary"]:active {
        transform: translateY(6px);
        box-shadow: 0 0 0 #1A6B63, 0 2px 5px rgba(0,0,0,0.2);
    }
    /* 搜尋按鈕 (橘紅色 3D) */
    .stLinkButton > a[kind="secondary"] {
        background: linear-gradient(to bottom, #E76F51, #D65A3F) !important;
        color: white !important;
        border: none;
        border-radius: 15px;
        padding: 18px 24px;
        font-size: 1.2rem !important;
        font-weight: 900 !important;
        width: 100%;
        text-align: center;
        text-decoration: none;
        display: block;
        box-shadow: 0 6px 0 #A83E26, 0 12px 15px rgba(0,0,0,0.2);
        transition: all 0.1s ease;
        margin-top: 10px;
    }
    .stLinkButton > a[kind="secondary"]:active {
        transform: translateY(6px);
        box-shadow: 0 0 0 #A83E26, 0 2px 5px rgba(0,0,0,0.2);
    }
    /* 按鈕文字強制白 */
    .stButton > button p, .stLinkButton > a { color: white !important; }

    /* 10. 卡片與氣泡 */
    div[data-testid="stVerticalBlock"] > div[style*="background-color"] {
        background-color: white !important;
        border-radius: 15px;
        padding: 20px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.05);
    }
    .stChatMessage {
        background-color: white !important;
        border-radius: 15px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    .stChatMessage p { color: #333 !important; }
    
    .stat-box small { color: #666 !important; }
    .stat-box b { color: #2A9D8F !important; }
    
    .step-header {
        font-size: 1.3rem;
        font-weight: bold;
        color: #2A9D8F !important;
        margin-bottom: 10px;
        border-bottom: 2px solid #E0E0E0;
        padding-bottom: 5px;
    }
    
    /* 隱藏開發者選單 (Optional, 保留您的設定) */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
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
        part1 = sin(dlat/2)**2
        part2 = cos(lat1) * cos(lat2) * sin(dlon/2)**2
        a = part1 + part2
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

# --- AI 核心 (🔥 強化連線穩定版) ---
def get_gemini_response(user_input):
    if not GOOGLE_API_KEY:
        return "⚠️ 請檢查 API Key", "low", "動物", "動物醫院"
    
    # 🔥 重試機制：針對 429 錯誤進行指數退避 (Exponential Backoff)
    max_retries = 3
    retry_delay = 5 # 初始等待 5 秒
    
    for attempt in range(max_retries):
        try:
            genai.configure(api_key=GOOGLE_API_KEY)
            
            # 🔥 確認使用 gemini-2.0-flash (您帳號支援的模型)
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
            
        except Exception as e:
            error_msg = str(e)
            # 如果不是最後一次嘗試，且錯誤包含 429 (配額限制)，則等待後重試
            if attempt < max_retries - 1:
                if "429" in error_msg:
                    time.sleep(retry_delay)
                    retry_delay *= 2 # 下次等久一點 (5s -> 10s -> 20s)
                    continue
                else:
                    return f"連線錯誤：{error_msg}", "low", "動物", "動物醫院"
            else:
                # 最後一次也失敗，若是 429 則顯示友善訊息
                if "429" in error_msg:
                    return "⚠️ 系統目前繁忙 (Google AI 流量管制)，請稍後再試。", "low", "動物", "動物醫院"
                return f"連線錯誤：{error_msg}", "low", "動物", "動物醫院"

# --- 每日知識 (同步更新模型) ---
def get_daily_tip():
    if not GOOGLE_API_KEY: return "請設定 API Key"
    try:
        genai.configure(api_key=GOOGLE_API_KEY)
        model = genai.GenerativeModel('gemini-2.0-flash') # 🔥 同步更新
        res = model.generate_content("給一個關於特殊寵物(爬蟲/鳥/兔)的有趣冷知識，50字內，繁體中文，開頭加上emoji")
        return res.text
    except:
        return "🐢 陸龜其實很喜歡曬太陽喔！"

# ====================
# 🖥️ 介面主程式
# ====================

# 1. Hero Header
st.markdown("""
    <div class="hero-container">
        <div class="hero-title">👨🏻‍⚕️ PetMatch AI智慧寵心導航</div>
        <div class="hero-subtitle">專為 🐱貓・🐶狗・🐢特寵 設計的AI醫療導航</div>
    </div>
""", unsafe_allow_html=True)

# 側邊欄 (系統狀態)
with st.sidebar:
    st.markdown("### ℹ️ 系統狀態")
    if GOOGLE_API_KEY:
        st.success("✅ AI 系統連線正常")
    else:
        st.error("⚠️ 未偵測到 API Key")
    
    st.markdown("---")
    st.markdown(f"""
    <div class="stat-box" style="text-align:center; padding:10px; background:#EFEFEF; border-radius:10px;">
        <small style="color:#666 !important;">目前資料庫收錄</small><br>
        <b style="font-size:1.5rem; color:#2A9D8F !important;">{len(HOSPITALS_DB)}</b> <small style="color:#666 !important;">家專科醫院</small>
    </div>
    """, unsafe_allow_html=True)
    st.caption("v15.1 穩定強化版")

# 主畫面分頁
tab_home, tab_news, tab_about = st.tabs(["🏥 智能導航", "📰 衛教專區", "ℹ️ 關於我們"])

# --- TAB 1: 智能導航 ---
with tab_home:
    
    # 預設位置 (楠梓)
    if 'current_pos' not in st.session_state:
        st.session_state.current_pos = {"lat": 22.7268, "lon": 120.2975}
        st.session_state.location_name = "高雄市 (楠梓區)"

    # ====== 區塊 1: 定位與地圖 (上方) ======
    with st.container(border=True):
        st.markdown('<div class="step-header">📍 第一步：確認您的位置</div>', unsafe_allow_html=True)
        
        col_gps_btn, col_map_view = st.columns([1, 2])
        
        with col_gps_btn:
            st.write("請先點擊下方按鈕進行定位，或使用手動切換功能：")
            
            if 'gps_activated' not in st.session_state:
                st.session_state.gps_activated = False

            # 🔥 按鈕文字修正：
