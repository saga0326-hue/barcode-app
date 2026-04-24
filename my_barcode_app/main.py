import streamlit as st
import pandas as pd
import requests
import json
import streamlit.components.v1 as components

# 1. 頁面基礎設定
st.set_page_config(
    page_title="專業商品條碼系統", 
    layout="wide", 
    page_icon="📦",
    initial_sidebar_state="collapsed" 
)

# --- 核心：九宮格數字鍵盤腳本 (針對 iPhone 優化) ---
def force_numeric_pad():
    components.html(
        """
        <script>
            const fixInputs = () => {
                const inputs = window.parent.document.querySelectorAll("input[type='number']");
                inputs.forEach(input => {
                    input.setAttribute("inputmode", "numeric");
                    input.setAttribute("pattern", "[0-9]*");
                });
            };
            const observer = new MutationObserver(fixInputs);
            observer.observe(window.parent.document.body, { childList: true, subtree: true });
            fixInputs();
        </script>
        """,
        height=0,
    )

# 2. 數據讀取邏輯 (30秒快取)
@st.cache_data(ttl=30)
def fetch_data(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        df = pd.read_csv(url, dtype=str, storage_options=headers)
        df.columns = df.columns.str.strip()
        for col in df.columns:
            df[col] = df[col].fillna("").astype(str).str.strip()
            if col == '條碼':
                df[col] = df[col].str.replace('*', '', regex=False)
        return df
    except Exception as e:
        return f"ERROR: {str(e)}"

# 3. 讀取 Secrets
try:
    DATA_URL = st.secrets["data_url"]
    CAT_URL = st.secrets["cat_url"]
    SCRIPT_URL = st.secrets.get("script_url", "")
except:
    st.error("❌ 請檢查 Secrets 設定")
    st.stop()

# --- 主程式執行 ---
force_numeric_pad()
st.markdown("### 🛡️ 團隊共享條碼系統")

df_main = fetch_data(DATA_URL)
df_cat = fetch_data(CAT_URL)

if isinstance(df_main, pd.DataFrame):
    # 使用極短標籤防止手機端換行
    tab_search, tab_add, tab_settings, tab_feedback = st.tabs(["🔍搜尋", "➕新增", "⚙️設定", "💬反映"])

    # --- Tab 1: 快速搜尋 ---
    with tab_search:
        # 使用迷你按鈕 (Segmented Control)
        unique_types = sorted([str(t) for t in df_cat['類型'].unique() if t and t != 'nan'])
        st.write("📂 **類別**")
        selected_type = st.segmented_control("type_sel", options=["全部"] + unique_types, default="全部", label_visibility="collapsed")
        
        st.write("🏦 **口座**")
        selected_koz = st.segmented_control("koz_sel", options=["全部", "04", "05", "07"], default="全部", label_visibility="collapsed")
        
        st.divider()
        search_name = st.text_input("📝 品名關鍵字", placeholder="輸入關鍵字...")
        search_code_num = st.number_input("🔢 條碼搜尋", step=1, value=None, key="search_bc_input")
        search_code = str(search_code_num) if search_code_num is not None else ""

        # 讀取排序
        is_asc = st.session_state.get('is_ascending', True)
        has_search = (search_name != "") or (search_code != "") or (selected_type != "全部") or (selected_koz != "全部")

        if has_search:
            work_df = df_main.copy() if selected_type == "全部" else df_cat[df_cat['類型'] == selected_type].copy()
            if selected_koz != "全部": 
                work_df = work_df[work_df['口座'] == selected_koz]
            if search_name: 
                work_df = work_df[work_df['品名'].str.contains(search_name, na=False, case=False)]
            if search_code: 
                work_df = work_df[work_df['條碼'].str.contains(search_code, na=False)]
            
            work_df = work_df.sort_values(by='品名', ascending=is_asc).head(50)

            for _, row in work_df.iterrows():
                with st.container(border=True):
                    c1, c2 = st.columns([1.5, 3])
                    with c1:
                        st.image(f"https://bwipjs-api.metafloor.com/?bcid=code128&text={row.get('條碼','')}&scale=2&includetext")
                    with c2:
                        st.markdown(f"**{row['品名']}**")
                        st.caption(f"口座: {row.get('口座','-')} | 代號: {row.get('商品代號','-')}")
        else:
            st.info("👋 請點選上方按鈕或輸入關鍵字搜尋")

    # --- Tab 2: 新增品項 ---
    with tab_add:
        st.markdown("#### ➕ 新增商品至 categories")
        st.write("選擇口座")
        new_koz = st.segmented_control("koz_add", ["04", "05", "07"], default="04", label_visibility="collapsed")
        st.write("選擇類別")
        chosen_type = st.segmented_control("type_add", unique_types + ["➕新增"], default=unique_types[0] if unique_types else "➕新增", label_visibility="collapsed")
        
        final_type = st.text_input("新類別名稱") if chosen_type == "➕新增" else chosen_type
        new_name = st.text_input("商品品名 (必填)")
        new_bc_num = st.number_input("商品條碼 (必填)", step=1, value=None, key="add_bc_num")
        
        if st.button("🚀 確認送出商品", use_container_width=True):
            if final_type and new_name and new_bc_num:
                payload = {
                    "method": "add_barcode", 
                    "type": final_type, 
                    "name": new_name, 
                    "barcode": str(new_bc_num),
                    "koz": new_koz
                }
                res = requests.post(SCRIPT_URL, data=json.dumps(payload))
                if "Success" in res.text:
                    st.success("✅ 已存入 categories")
                    st.cache_data.clear()
                else: st.error(f"失敗: {res.text}")

    # --- Tab 3: 設定 ---
    with tab_settings:
        st.markdown("#### 🔃 排序設定")
        sort_choice = st.radio("排序方式", ["遞增 (A-Z)", "遞減 (Z-A)"], index=0)
        st.session_state['is_ascending'] = (sort_choice == "遞增 (A-Z)")
        
        if st.button("🔄 刷新資料庫快取", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    # --- Tab 4: 意見反映 (已修復 fb_payload 錯誤) ---
    with tab_feedback:
        st.markdown("#### 💬 意見反映")
        fb_type = st.selectbox("類型", ["功能建議", "錯誤回報", "資料修正", "其他"])
        fb_user = st.text_input("您的稱呼", placeholder="匿名")
        fb_content = st.text_area("內容 (必填)")
        
        if st.button("🚀 提交意見", use_container_width=True):
            if fb_content.strip():
                # 統一使用 payload，避免 NameError
                payload = {
                    "method": "feedback", 
                    "type": fb_type, 
                    "user": fb_user if fb_user else "匿名", 
                    "content": fb_content
                }
                try:
                    res = requests.post(SCRIPT_URL, data=json.dumps(payload), timeout=15)
                    if "Success" in res.text:
                        st.success("✅ 感謝您的回饋！")
                        st.balloons()
                    else:
                        st.error(f"❌ 提交失敗: {res.text}")
                except Exception as e:
                    st.error(f"❌ 連線出錯: {str(e)}")
            else:
                st.warning("⚠️ 內容不可為空")
else:
    st.error("⚠️ 資料源連線失敗")
