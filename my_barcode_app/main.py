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

# --- 核心：強制九宮格鍵盤腳本 ---
def force_numeric_pad():
    components.html(
        """
        <script>
            // 持續監控並修正輸入框屬性
            const fixInputs = () => {
                var inputs = window.parent.document.querySelectorAll("input[type='number']");
                for (var i = 0; i < inputs.length; i++) {
                    // inputmode="numeric" 會喚起九宮格數字鍵盤
                    inputs[i].setAttribute("inputmode", "numeric");
                    // pattern 確保某些行動瀏覽器更精準識別
                    inputs[i].setAttribute("pattern", "[0-9]*");
                }
            };
            // 執行一次並設定定時器處理 Streamlit 重新渲染的情況
            fixInputs();
            setTimeout(fixInputs, 1000);
            setTimeout(fixInputs, 3000);
        </script>
        """,
        height=0,
    )

# 2. 數據讀取與快取邏輯
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

# 3. 讀取 Secrets 設定
try:
    DATA_URL = st.secrets["data_url"]
    CAT_URL = st.secrets["cat_url"]
    SCRIPT_URL = st.secrets.get("script_url", "")
except:
    st.error("❌ 請檢查 .streamlit/secrets.toml 設定")
    st.stop()

# --- 主程式開始 ---
st.markdown("### 🛡️ 團隊共享條碼系統")
# 呼叫強制鍵盤腳本
force_numeric_pad()

df_main = fetch_data(DATA_URL)
df_cat = fetch_data(CAT_URL)

if isinstance(df_main, pd.DataFrame):
    tab_search, tab_add, tab_settings = st.tabs(["🔍 快速搜尋", "➕ 新增品項", "⚙️ 設定"])

    # --- Tab 3: 系統設定 ---
    with tab_settings:
        st.markdown("#### 🖼️ 顯示設定")
        img_size = st.slider("調整條碼/圖片大小", 50, 400, 150, 10)
        sort_choice = st.radio("搜尋結果排序方式 (依品名)", ["遞增 (A-Z)", "遞減 (Z-A)"], index=0)
        is_ascending = True if sort_choice == "遞增 (A-Z)" else False
        
        if st.button("強制重新整理資料庫", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    # --- Tab 1: 快速搜尋 ---
    with tab_search:
        unique_types = sorted([str(t) for t in df_cat['類型'].unique() if t and t != 'nan'])
        selected_type = st.selectbox("📂 選擇類別", ["全部"] + unique_types)
        search_name = st.text_input("📝 品名關鍵字", placeholder="輸入品名搜尋...")
        
        # 使用 number_input 配合腳本喚起九宮格
        search_code_num = st.number_input("🔢 條碼搜尋", step=1, value=None, placeholder="點擊輸入數字...")
        search_code = str(search_code_num) if search_code_num is not None else ""

        has_search = (search_name != "") or (search_code != "") or (selected_type != "全部")

        if has_search:
            work_df = df_main.copy() if selected_type == "全部" else df_cat[df_cat['類型'] == selected_type].copy()
            if search_name:
                work_df = work_df[work_df['品名'].str.contains(search_name, na=False, case=False)]
            if search_code:
                mask = work_df['條碼'].str.contains(search_code, na=False)
                if '商品代號' in work_df.columns:
                    mask |= work_df['商品代號'].str.contains(search_code, na=False)
                work_df = work_df[mask]

            work_df = work_df.sort_values(by='品名', ascending=is_ascending).head(50)

            if not work_df.empty:
                st.caption(f"找到 {len(work_df)} 筆結果")
                for _, row in work_df.iterrows():
                    bc_val = row.get('條碼', '')
                    with st.container(border=True):
                        c1, c2 = st.columns([1.5, 3])
                        with c1:
                            if bc_val:
                                st.image(f"https://bwipjs-api.metafloor.com/?bcid=code128&text={bc_val}&scale=2&includetext", width=img_size)
                            else:
                                st.caption("無條碼資訊")
                        with c2:
                            st.markdown(f"**{row['品名']}**")
                            st.caption(f"口座: `{row.get('口座', '-')}` | 代號: `{row.get('商品代號', '-')}`")
            else:
                st.warning("查無符合資料")
        else:
            st.info("👋 請輸入搜尋關鍵字或選擇類別")

    # --- Tab 2: 新增品項 ---
    with tab_add:
        st.markdown("#### ➕ 新增商品資訊")
        type_options = unique_types + ["➕ 新增其他類別..."]
        chosen_type = st.selectbox("選擇類別", type_options, key="add_type")
        final_type = st.text_input("新類別名稱") if chosen_type == "➕ 新增其他類別..." else chosen_type
        new_name = st.text_input("商品品名 (必填)", placeholder="請輸入完整名稱")
        
        # 使用 number_input 配合腳本喚起九宮格
        new_bc_num = st.number_input("商品條碼 (必填)", step=1, value=None, placeholder="輸入數字條碼")
        new_bc = str(new_bc_num) if new_bc_num is not None else ""
        
        status_msg = st.empty()
        
        if st.button("🚀 確認送出並寫入", use_container_width=True):
            if final_type and new_name and new_bc:
                status_msg.info("⏳ 處理中，請稍候...")
                payload = {"type": final_type, "name": new_name, "barcode": new_bc}
                try:
                    headers = {'Content-Type': 'application/json'}
                    res = requests.post(SCRIPT_URL, data=json.dumps(payload), headers=headers, timeout=15)
                    status_msg.empty()
                    if "Success" in res.text:
                        st.success("✅ 寫入成功！")
                        st.cache_data.clear()
                    else: 
                        st.error(f"❌ 失敗: {res.text}")
                except Exception as e: 
                    status_msg.empty()
                    st.error(f"❌ 連線失敗: {str(e)}")
            else: 
                st.warning("⚠️ 請填寫所有必要欄位")
else:
    st.error("⚠️ 資料源連線失敗")
