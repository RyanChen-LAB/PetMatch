import streamlit as st
import google.generativeai as genai
import time

# --- 設定頁面 ---
st.set_page_config(page_title="Gemini 模型額度檢測", page_icon="🧪")

st.title("🧪 Google Gemini 模型額度檢測器")
st.caption("此工具會對您的 API Key 可用的所有模型發送測試請求，以確認哪些目前可用。")

# --- 輸入 API Key ---
# 嘗試從 secrets 讀取，如果沒有就讓使用者輸入
default_key = ""
try:
    default_key = st.secrets["GOOGLE_API_KEY"]
except:
    pass

api_key = st.text_input("請輸入您的 Google API Key", value=default_key, type="password")

if st.button("🚀 開始檢測", type="primary"):
    if not api_key:
        st.error("請先輸入 API Key")
    else:
        genai.configure(api_key=api_key)
        
        status_container = st.container()
        results = []
        
        with st.spinner("正在掃描您的帳號權限..."):
            try:
                # 1. 抓取所有支援 'generateContent' 的模型
                all_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                st.write(f"📋 您的帳號共擁有 **{len(all_models)}** 個生成式模型權限。")
                st.divider()
                
                # 2. 逐一測試
                progress_bar = st.progress(0)
                
                for i, model_name in enumerate(all_models):
                    display_name = model_name.replace("models/", "")
                    
                    try:
                        # 測試連線
                        model = genai.GenerativeModel(model_name)
                        start_time = time.time()
                        response = model.generate_content("Hi", request_options={"timeout": 5})
                        end_time = time.time()
                        duration = end_time - start_time
                        
                        if response.text:
                            results.append({"name": display_name, "status": "✅ 可用", "time": f"{duration:.2f}s", "msg": "額度充足"})
                        
                    except Exception as e:
                        error_msg = str(e)
                        if "429" in error_msg:
                            results.append({"name": display_name, "status": "❌ 額度滿", "time": "-", "msg": "Quota Exceeded (429)"})
                        elif "404" in error_msg:
                            results.append({"name": display_name, "status": "⚠️ 停用", "time": "-", "msg": "Not Found (404)"})
                        else:
                            results.append({"name": display_name, "status": "❓ 錯誤", "time": "-", "msg": "Other Error"})
                    
                    # 更新進度條
                    progress_bar.progress((i + 1) / len(all_models))
                    time.sleep(0.5) # 稍微暫停避免測試本身觸發限流

            except Exception as e:
                st.error(f"讀取模型清單失敗：{e}")

        # --- 3. 顯示結果報告 ---
        st.subheader("📊 檢測報告")
        
        # 分類顯示
        available = [r for r in results if "✅" in r['status']]
        unavailable = [r for r in results if "❌" in r['status']]
        
        c1, c2 = st.columns(2)
        
        with c1:
            st.success(f"🟢 目前可用：{len(available)} 個")
            for r in available:
                st.markdown(f"- **`{r['name']}`** ({r['time']})")
                
        with c2:
            st.error(f"🔴 目前額度已滿：{len(unavailable)} 個")
            for r in unavailable:
                st.markdown(f"- `{r['name']}`")

        # 建議
        if available:
            best_model = available[0]['name']
            st.info(f"💡 建議：請將您的 `PM.py` 中的模型名稱改為 **`{best_model}`**")
