import streamlit as st
import google.generativeai as genai

# 設定頁面
st.set_page_config(page_title="模型檢測工具", layout="wide")

# 讀取 API Key
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
    
    st.subheader("🤖 您的 API Key 可用的 Gemini 模型清單：")
    
    # 抓取所有模型
    models = genai.list_models()
    
    found_models = []
    for m in models:
        # 只顯示支援 "generateContent" (對話生成) 的模型
        if 'generateContent' in m.supported_generation_methods:
            found_models.append(m.name)
            st.write(f"- `{m.name}`")
            
    st.success(f"共找到 {len(found_models)} 個可用模型")
    
    # 特別檢查 gemini-1.5-flash
    if "models/gemini-1.5-flash" in found_models:
        st.info("✅ 推薦使用：`gemini-1.5-flash` (速度快、免費額度高)")
    else:
        st.warning("⚠️ 未找到 gemini-1.5-flash，請檢查您的 API Key 權限")

except Exception as e:
    st.error(f"無法讀取模型清單，錯誤原因：{e}")
