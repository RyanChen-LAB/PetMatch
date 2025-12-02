import streamlit as st
import pandas as pd
import google.generativeai as genai
import folium
import streamlit.components.v1 as components
from streamlit_js_eval import get_geolocation 
from math import radians, cos, sin, asin, sqrt

# --- 1. 頁面設定 ---
st.set_page_config(page_title="PetMatch AI智慧寵心導航", page_icon="🐾", layout="wide")

# ====== 🎨 CSS 強制顯色與 3D 按鈕樣式 ======
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;700&family=Nunito:wght@700&display=swap');
    
    /* 1. 全域強制設定：背景淺色，文字深色 */
    :root {
        --primary-color: #2A9D8F;
        --text-color: #264653;
    }
    
    html, body, [class*="css"], .stApp {
        font-family: 'Noto Sans TC', sans-serif;
        color: #264653 !important;
        background-color: #F9F7F2 !important;
    }

    /* 2. 強制文字顏色，避免手機深色模式隱形 */
    .stMarkdown p, .stMarkdown span, .stMarkdown div, 
    h1, h2, h3, h4, h5, h6, 
    label, .stText, .stHtml, .stCaption, .stMarkdown {
        color: #264653 !important;
    }

    /* 3. Hero Header (維持白色) */
    .hero-container {
        background: linear-gradient(120deg, #264653, #2A9D8F);
        padding: 30px;
        border-radius: 20px;
        color: white !important;
        text-align: center;
        box-shadow: 0 10px 20px rgba(42, 157, 143, 0.2);
        margin-bottom: 25px;
    }
    .hero-title { font-family: 'Nunito', sans-serif; font-size: 2.2rem; font-weight: 800; margin: 0; color: white !important; }
    .hero-subtitle { font-size: 1rem; opacity: 0.9; margin-top: 5px; color: white !important; }
    
    /* 強制 Hero 內文字白 */
    .hero-container * { color: white !important; }

    /* 4. 🔥 3D 超大定位按鈕專屬樣式 🔥 */
    /* 針對 Primary Button 做特效 */
    .stButton > button[kind="primary"] {
        background: linear-gradient(to bottom, #2A9D8F, #21867a) !important;
        color: white !important;
        border: none;
        border-radius: 15px;
        padding: 20px 10px; /* 加大高度 */
        font-size: 2.0 rem !important; /* 加大字體 */
        font-weight: 900 !important;
        width: 100%;
        text-shadow: 0px 1px 2px rgba(0,0,0,0.3);
        
        /* 3D 立體陰影 */
        box-shadow: 0 6px 0 #1A6B63, 0 12px 15px rgba(0,0,0,0.2);
        transition: all 0.1s ease;
        margin-bottom: 15px;
    }
    
    /* 按下去的效果 */
    .stButton > button[kind="primary"]:active {
        transform: translateY(6px); /* 真實下壓感 */
        box-shadow: 0 0 0 #1A6B63, 0 2px 5px rgba(0,0,0,0.2);
    }
    
    /* 按鈕內的文字強制白色 */
    .stButton > button p { color: white !important; }

    /* 一般次要按鈕 */
    .stButton > button[kind="secondary"] {
        background-color: #ffffff !important;
        color: #2A9D8F !important;
        border: 2px solid #2A9D8F;
        border-radius: 12px;
    }

    /* 5. 卡片與氣泡 */
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
    
    .stat-box small { color: #666 !important; }
    .stat-box b { color: #2A9D8F !important; }
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
    if not GOOGLE_API_KEY: return "請設定 API Key"
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
         <div class="hero-title"> 👨🏻‍⚕️ PetMatch AI智慧寵心導航</div>
         <div class="hero-subtitle">專為 🐱貓・🐶狗・🐢特寵 設計的AI醫療導航</div>
    </div>
""", unsafe_allow_html=True)

# 側邊欄保持乾淨
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
    st.caption("v4.9 3D 按鈕版")

# 主畫面分頁
tab_home, tab_news, tab_about = st.tabs(["🏥 智能導航", "📰 衛教專區", "ℹ️ 關於我們"])

# --- TAB 1: 智能導航 ---
with tab_home:
    col_chat, col_map = st.columns([2, 1.2])
    
    # 預設位置 (楠梓)
    default_pos = {"lat": 22.7268, "lon": 120.2975} 
    current_user_pos = default_pos

    # ====== 右側：地圖與定位 ======
    with col_map:
        with st.container(border=True):
            st.markdown("### 📍 第一步先定位！")
            
            # --- 🚀 全新設計：3D 大按鈕取代 Toggle ---
            # 使用 Session State 記住定位狀態
            if 'gps_activated' not in st.session_state:
                st.session_state.gps_activated = False

            # 按鈕：使用 primary 樣式觸發 CSS 3D 特效
            if st.button("📍 點擊啟用 GPS 自動定位", type="primary", use_container_width=True):
                st.session_state.gps_activated = True
                st.rerun() # 立即刷新執行定位

            # 執行定位邏輯
            if st.session_state.gps_activated:
                gps_location = get_geolocation(component_key='get_loc')
                
                if gps_location and gps_location.get('coords'):
                    current_user_pos = {
                        "lat": gps_location['coords']['latitude'],
                        "lon": gps_location['coords']['longitude']
                    }
                    st.success("✅ 定位完成！")
                else:
                    st.warning("📡 定位中... 請允許瀏覽器權限")
            else:
                st.info("👆 請點擊上方大按鈕開始")
        
        # 2. 手動校正 (摺疊)
        with st.expander("🔧 定位不準？手動切換"):
            kaohsiung_coords = {
                "楠梓區": {"lat": 22.7268, "lon": 120.2975},
                "左營區": {"lat": 22.6800, "lon": 120.3000},
                "三民區": {"lat": 22.6496, "lon": 120.3292},
                "鼓山區": {"lat": 22.6368, "lon": 120.2795},
                "苓雅區": {"lat": 22.6204, "lon": 120.3123},
                "新興區": {"lat": 22.6293, "lon": 120.3023},
                "前金區": {"lat": 22.6277, "lon": 120.2936},
                "鹽埕區": {"lat": 22.6247, "lon": 120.2835},
                "前鎮區": {"lat": 22.5864, "lon": 120.3180},
                "旗津區": {"lat": 22.5694, "lon": 120.2778},
                "小港區": {"lat": 22.5656, "lon": 120.3542},
                "鳳山區": {"lat": 22.6269, "lon": 120.3574},
                "鳥松區": {"lat": 22.6593, "lon": 120.3639},
                "仁武區": {"lat": 22.7016, "lon": 120.3468},
                "大社區": {"lat": 22.7315, "lon": 120.3475},
                "大寮區": {"lat": 22.6053, "lon": 120.3957},
                "林園區": {"lat": 22.5029, "lon": 120.3949},
                "大樹區": {"lat": 22.6937, "lon": 120.4334},
                "橋頭區": {"lat": 22.7575, "lon": 120.3056},
                "岡山區": {"lat": 22.7960, "lon": 120.2960},
                "路竹區": {"lat": 22.8546, "lon": 120.2612},
                "阿蓮區": {"lat": 22.8837, "lon": 120.3274},
                "湖內區": {"lat": 22.9037, "lon": 120.2223},
                "茄萣區": {"lat": 22.9064, "lon": 120.1824},
                "永安區": {"lat": 22.8202, "lon": 120.2272},
                "彌陀區": {"lat": 22.7828, "lon": 120.2452},
                "梓官區": {"lat": 22.7607, "lon": 120.2657},
                "燕巢區": {"lat": 22.7932, "lon": 120.3606},
                "田寮區": {"lat": 22.8753, "lon": 120.3619},
                "旗山區": {"lat": 22.8885, "lon": 120.4822},
                "美濃區": {"lat": 22.9006, "lon": 120.5376},
                "內門區": {"lat": 22.9464, "lon": 120.4578},
                "杉林區": {"lat": 22.9696, "lon": 120.5332},
                "甲仙區": {"lat": 23.0841, "lon": 120.5898},
                "六龜區": {"lat": 23.0033, "lon": 120.6333},
                "茂林區": {"lat": 22.8906, "lon": 120.6623},
                "桃源區": {"lat": 23.1593, "lon": 120.7634},
                "那瑪夏區": {"lat": 23.2393, "lon": 120.6970}
            }
            manual_area = st.selectbox(
                "👇 點此選擇正確區域：",
                list(kaohsiung_coords.keys())
            )
            
            if not st.session_state.gps_activated:
                current_user_pos = kaohsiung_coords[manual_area]
                st.info(f"📍 已手動切換至：{manual_area}")

        # 3. 預覽地圖
        m_preview = folium.Map(location=[current_user_pos["lat"], current_user_pos["lon"]], zoom_start=13)
        folium.Marker(
            [current_user_pos["lat"], current_user_pos["lon"]], 
            icon=folium.Icon(color="blue", icon="user"), 
            popup="您的位置"
        ).add_to(m_preview)
        
        if HOSPITALS_DB:
            for h in HOSPITALS_DB:
                folium.CircleMarker(
                    location=[h['lat'], h['lon']],
                    radius=5, color="green", fill=True, fill_opacity=0.7
                ).add_to(m_preview)
                
        components.html(m_preview._repr_html_(), height=250)

    # ====== 左側：AI 對話 ======
    with col_chat:
        st.markdown("### 💬 AI 醫療助理")
        
        if "messages" not in st.session_state:
            st.session_state.messages = [{"role": "assistant", "content": "嗨！我是 AI 醫療助理。請告訴我您的寵物怎麼了？"}]

        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])

        if prompt := st.chat_input("輸入症狀 (例如：守宮不吃東西)..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            st.chat_message("user").write(prompt)

            with st.chat_message("assistant"):
                with st.spinner("🧠 AI 正在分析並搜尋 10km 內資源..."):
                    reply_text, urgency_level, animal_type, search_keywords = get_gemini_response(prompt)
                    st.write(reply_text)
                    st.session_state.messages.append({"role": "assistant", "content": reply_text})
                    
                    vip_hospitals = []
                    min_dist = 9999
                    
                    if HOSPITALS_DB:
                        for h in HOSPITALS_DB:
                            dist = calculate_distance(current_user_pos['lat'], current_user_pos['lon'], h['lat'], h['lon'])
                            h['distance_km'] = round(dist, 1)
                            if dist < min_dist: min_dist = dist
                            
                            tags_str = str(h['tags'])
                            is_match = False
                            if animal_type in tags_str or any(k in tags_str for k in search_keywords.split()):
                                is_match = True
                            if urgency_level == "high" and ("24H" in tags_str or "急診" in tags_str):
                                is_match = True
                            
                            if is_match and dist < 10.0: 
                                vip_hospitals.append(h)

                    vip_hospitals.sort(key=lambda x: x['distance_km'])

                    st.markdown("---")
                    
                    if min_dist > 20:
                        st.warning(f"⚠️ 最近醫院距離 {int(min_dist)} 公里，定位可能不準，請手動調整。")

                    if urgency_level == "high":
                        st.error(f"🚨 高度緊急！AI 建議搜尋：{search_keywords}")
                    else:
                        st.info(f"ℹ️ 醫療建議類別：{animal_type}")

                    # --- 推薦結果 ---
                    if vip_hospitals:
                        st.subheader(f"🏆 10公里內推薦 ({len(vip_hospitals)} 家)")
                        for h in vip_hospitals:
                            with st.container():
                                c1, c2 = st.columns([3, 1])
                                with c1:
                                    st.markdown(f"### 🏅 {h['name']}")
                                    st.markdown(f"**距離：{h['distance_km']} 公里** | ⭐ {h['rating']} | {h['status']}")
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
                            st.write("") 
                    else:
                        st.warning(f"⚠️ 附近 10 公里內暫無資料庫認證的 **{animal_type}** 醫院。")

                    st.markdown("#### 沒找到合適的？")
                    gmap_query = f"https://www.google.com/maps/search/?api=1&query={search_keywords}"
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
