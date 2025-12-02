import streamlit as st
import pandas as pd
import google.generativeai as genai
import folium
import streamlit.components.v1 as components
from streamlit_js_eval import get_geolocation 
from math import radians, cos, sin, asin, sqrt

# --- 1. 頁面設定 ---
st.set_page_config(page_title="PetMatch AI智慧寵心導航", page_icon="🐾", layout="wide")

# ====== 🎨 CSS 終極修復：強制淺色 + 手機優化 + 3D按鈕 ======
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

    /* 3. 強制所有文字元素顯色 */
    .stMarkdown p, .stMarkdown span, .stMarkdown div, 
    h1, h2, h3, h4, h5, h6, 
    label, .stText, .stHtml, .stCaption {
        color: #264653 !important;
    }

    /* 4. 分頁標籤 (Tabs) 顯色修復 */
    button[data-baseweb="tab"] { color: #264653 !important; }
    button[data-baseweb="tab"] div p {
        color: #264653 !important;
        font-weight: 700 !important;
        font-size: 1.1rem !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        border-bottom-color: #2A9D8F !important;
    }

    /* 5. 輸入框文字顏色 */
    .stTextInput input {
        color: #264653 !important;
        background-color: #FFFFFF !important;
    }

    /* 6. Hero Header */
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
        font-size: 1rem; 
        opacity: 1; 
        margin-top: 5px; 
        font-weight: 700; 
        color: #2A9D8F !important; 
        letter-spacing: 1px; 
    }

    /* 7. 3D 大按鈕 (定位用) */
    .stButton > button[kind="primary"] {
        background: linear-gradient(to bottom, #2A9D8F, #21867a) !important;
        color: white !important;
        border: none;
        border-radius: 15px;
        padding: 18px 24px;
        font-size: 1.2rem !important;
        font-weight: 900 !important;
        width: 100%;
        text-shadow: 0px 1px 2px rgba(0,0,0,0.3);
        box-shadow: 0 6px 0 #1A6B63, 0 12px 15px rgba(0,0,0,0.2);
        transition: all 0.1s ease;
        margin-bottom: 15px;
        display: flex;
        justify-content: center;
        align-items: center;
    }
    .stButton > button[kind="primary"]:active {
        transform: translateY(6px);
        box-shadow: 0 0 0
