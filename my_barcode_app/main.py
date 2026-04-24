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

# --- 核心：九宮格數字鍵盤腳本 (確保手機輸入體驗) ---
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

# 2. 數據讀取邏輯
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
    # 分頁名稱保持簡短，避免手機端導覽列擠壓
    tab_search, tab_add, tab_settings, tab_feedback = st.tabs(["🔍搜尋", "➕新增", "⚙️設定", "💬反映"])

    # --- Tab 3: 設定 (排序功能放在這裡) ---
    with tab_settings:
        st.markdown("#### 🔃 排序設定")
        sort_choice = st.radio("搜尋結果排序方式 (依品名)", ["遞增 (A-Z)", "遞減 (Z-A)"], index=0)
        is_ascending = True if sort_choice == "遞增 (A-Z)" else False
        
        st.divider()
        if st.button("🔄 刷新資料庫快取", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    # --- Tab 1: 快速搜尋 (回歸簡潔單行排列) ---
    with tab_search:
        unique_types = sorted([str(t) for t in df_cat['類型'].unique() if t and t != 'nan'])
        selected_type = st.selectbox("📂 選擇類別", ["全部"] + unique_types)

        search_name = st.text_input("📝 品名關鍵字", placeholder="輸入名稱搜尋...")
        
        # 觸發九宮格的條碼搜尋框
        search_code_num = st.number_input("🔢 條碼搜尋", step=1, value=None, key="main_search_bc")
        search_code = str(search_code_num) if search_code_num is not None else ""

        # 綜合篩選邏輯
        has_search = (search_name != "") or (search_code != "") or (selected_type != "全部")

        if has_search:
            work_df = df_main.copy() if selected_type == "全部" else df_cat[df_cat['類型'] == selected_type].copy()
            
            if search_name:
                work_df = work_df[work_df['品名'].str.contains(search_name, na=False, case=False)]
            if search_code:
                work_df = work_df[work_df['條碼'].str.contains(search_code, na=False)]
            
            # 排序與顯示限制
            work_df = work_df.sort_values(by='品名', ascending=is_ascending).head(50)

            if not work_df.empty:
                st.caption(f"找到 {len(work_df)} 筆結果 (排序: {sort_choice})")
                for _, row in work_df.iterrows():
                    bc_val = row.get('條碼', '')
                    with st.container(border=True):
                        col_img, col_txt = st.columns([1.5, 3])
                        with col_img:
                            if bc_val:
                                st.image(f"https://bwipjs-api.metafloor.com/?bcid=code128&text={bc_val}&scale=2&includetext")
                            else: st.caption("無條碼")
                        with col_txt:
                            st.markdown(f"**{row['品名']}**")
                            st.caption(f"口座: `{row.get('口座', '-')}` | 代號: `{row.get('商品代號', '-')}`")
            else:
                st.warning("查無符合資料")
        else:
            st.info("👋 請輸入關鍵字或選擇類別開始搜尋")

    # --- Tab 2: 新增品項 ---
    with tab_add:
        st.markdown("#### ➕ 新增商品資訊")
        chosen_type = st.selectbox("選擇類別", unique_types + ["➕ 新增類別..."], key="add_t_box")
        final_type = st.text_input("新類別名稱") if chosen_type == "➕ 新增類別..." else chosen_type
        new_name = st.text_input("商品品名 (必填)")
        new_bc_num = st.number_input("商品條碼 (必填)", step=1, value=None, key="add_bc_num")
        
        if st.button("🚀 確認送出並寫入", use_container_width=True):
            if final_type and new_name and new_bc_num:
                payload = {
                    "method": "add_barcode", 
                    "type": final_type, 
                    "name": new_name, 
                    "barcode": str(new_bc_num)
                }
                requests.post(SCRIPT_URL, data=json.dumps(payload))
                st.success("成功寫入 categories！")
                st.cache_data.clear()
            else:
                st.warning("請填寫所有必要欄位")

    # --- Tab 4: 意見反映 ---
    with tab_feedback:
        st.markdown("#### 💬 意見反映")
        fb_content = st.text_area("反映內容")
        if st.button("🚀 提交意見", use_container_width=True):
            if fb_content:
                payload = {"method": "feedback", "type": "意見回饋", "user": "匿名", "content": fb_content}
                requests.post(SCRIPT_URL, data=json.dumps(payload))
                st.success("已收到您的回饋，謝謝！")
                st.balloons()
else:
    st.error("⚠️ 資料源連線失敗")
