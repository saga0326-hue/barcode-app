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

# --- 核心：九宮格數字鍵盤腳本 (加強版) ---
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
            // 監控頁面變動，防止切換 Tab 後失效
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
    # 四大功能分頁
    tab_search, tab_add, tab_settings, tab_feedback = st.tabs(["🔍 快速搜尋", "➕ 新增品項", "⚙️ 設定", "💬 意見反映"])

    # --- Tab 3: 設定 (優先定義，讓排序參數生效) ---
    with tab_settings:
        st.markdown("#### 🔃 排序設定")
        # 修正：預設改為 遞增 (A-Z)，index=0
        sort_choice = st.radio("搜尋結果排序方式 (依品名)", ["遞增 (A-Z)", "遞減 (Z-A)"], index=0)
        is_ascending = True if sort_choice == "遞增 (A-Z)" else False
        
        st.divider()
        if st.button("🔄 手動刷新資料庫", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    # --- Tab 1: 快速搜尋 ---
    with tab_search:
        unique_types = sorted([str(t) for t in df_cat['類型'].unique() if t and t != 'nan'])
        selected_type = st.selectbox("📂 選擇類別", ["全部"] + unique_types)
        search_name = st.text_input("📝 品名關鍵字", placeholder="搜尋品名...")
        search_code_num = st.number_input("🔢 條碼搜尋", step=1, value=None, key="search_bar")
        search_code = str(search_code_num) if search_code_num is not None else ""

        if (search_name != "") or (search_code != "") or (selected_type != "全部"):
            work_df = df_main.copy() if selected_type == "全部" else df_cat[df_cat['類型'] == selected_type].copy()
            if search_name: 
                work_df = work_df[work_df['品名'].str.contains(search_name, na=False, case=False)]
            if search_code: 
                work_df = work_df[work_df['條碼'].str.contains(search_code, na=False)]
            
            # 使用 Tab 3 的排序參數
            work_df = work_df.sort_values(by='品名', ascending=is_ascending).head(50)

            st.caption(f"排序：{sort_choice}")
            for _, row in work_df.iterrows():
                bc_val = row.get('條碼', '')
                with st.container(border=True):
                    c1, c2 = st.columns([1.5, 3])
                    with c1:
                        if bc_val:
                            st.image(f"https://bwipjs-api.metafloor.com/?bcid=code128&text={bc_val}&scale=2&includetext")
                        else: st.caption("無條碼")
                    with c2:
                        st.markdown(f"**{row['品名']}**")
                        st.caption(f"代號: `{row.get('商品代號', '-')}`")
        else:
            st.info("👋 請輸入關鍵字開始搜尋")

    # --- Tab 2: 新增品項 ---
    with tab_add:
        st.markdown("#### ➕ 新增商品資訊")
        chosen_type = st.selectbox("選擇類別", unique_types + ["➕ 新增類別..."], key="add_type_sel")
        final_type = st.text_input("新類別名稱") if chosen_type == "➕ 新增類別..." else chosen_type
        new_name = st.text_input("商品品名 (必填)")
        new_bc_num = st.number_input("商品條碼 (必填)", step=1, value=None, key="add_barcode_num")
        new_bc = str(new_bc_num) if new_bc_num is not None else ""
        
        status_add = st.empty()
        if st.button("🚀 確認送出商品", use_container_width=True):
            if final_type and new_name and new_bc:
                status_add.info("⏳ 處理中...")
                payload = {"method": "add_barcode", "type": final_type, "name": new_name, "barcode": new_bc}
                res = requests.post(SCRIPT_URL, data=json.dumps(payload), timeout=15)
                status_add.empty()
                if "Success" in res.text:
                    st.success("✅ 已存入 categories 分頁")
                    st.cache_data.clear()
                else: st.error(f"錯誤: {res.text}")
            else: st.warning("請填寫完整資訊")

    # --- Tab 4: 意見反映 ---
    with tab_feedback:
        st.markdown("#### 💬 意見反映")
        fb_type = st.selectbox("反映類型", ["功能建議", "錯誤回報", "資料修正", "其他"])
        fb_user = st.text_input("您的稱呼", placeholder="匿名")
        fb_content = st.text_area("反映內容")
        
        status_fb = st.empty()
        if st.button("🚀 提交意見", use_container_width=True):
            if fb_content:
                status_fb.info("⏳ 提交中...")
                payload = {
                    "method": "feedback", 
                    "type": fb_type, 
                    "user": fb_user if fb_user else "匿名", 
                    "content": fb_content
                }
                res = requests.post(SCRIPT_URL, data=json.dumps(payload), timeout=15)
                status_fb.empty()
                if "Success" in res.text:
                    st.success("✅ 意見已存入 feedback 分頁")
                    st.balloons()
                else: st.error(f"提交失敗: {res.text}")
            else: st.warning("內容不能為空")

else:
    st.error("⚠️ 資料源連線失敗")
