import streamlit as st
import pandas as pd
import requests
import json
import streamlit.components.v1 as components

# 1. 基本頁面設定 (針對手機優化)
st.set_page_config(
    page_title="專業商品條碼系統", 
    layout="wide", 
    page_icon="📦",
    initial_sidebar_state="collapsed" # 預設收起側邊欄，讓主畫面空間最大化
)

# --- 核心：強制手機跳出數字鍵盤的 JavaScript ---
def force_numeric_keyboard():
    components.html(
        """
        <script>
            var input = window.parent.document.querySelectorAll("input[type='text']");
            for (var i = 0; i < input.length; i++) {
                input[i].setAttribute("inputmode", "numeric");
                input[i].setAttribute("pattern", "[0-9]*");
            }
        </script>
        """,
        height=0,
    )

# 2. 數據讀取函式
@st.cache_data(ttl=60)
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

# 3. 取得設定資訊 (Secrets)
try:
    DATA_URL = st.secrets["data_url"]
    CAT_URL = st.secrets["cat_url"]
    SCRIPT_URL = st.secrets.get("script_url", "")
except:
    st.error("❌ 請檢查 .streamlit/secrets.toml 設定")
    st.stop()

# --- 主頁面開始 ---
st.title("🛡️ 團隊共享條碼系統")
force_numeric_keyboard()

df_main = fetch_data(DATA_URL)
df_cat = fetch_data(CAT_URL)

if isinstance(df_main, pd.DataFrame):
    # 使用 Tabs 分隔功能，手機操作更順手
    tab_search, tab_add, tab_settings = st.tabs(["🔍 快速搜尋", "➕ 新增品項", "⚙️ 系統設定"])

    # --- Tab 1: 搜尋與顯示 ---
    with tab_search:
        col_type, col_sort = st.columns([2, 1])
        unique_types = sorted([str(t) for t in df_cat['類型'].unique() if t and t != 'nan'])
        
        with col_type:
            selected_type = st.selectbox("📂 類別快選", ["全部"] + unique_types)
        with col_sort:
            sort_order = st.radio("排序", ["遞增", "遞減"], horizontal=True)

        search_name = st.text_input("📝 品名關鍵字", placeholder="例如：洗髮精...")
        search_code = st.text_input("🔢 條碼/代號搜尋", placeholder="點擊自動跳出數字鍵盤...")

        # 核心搜尋邏輯
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

            is_ascending = (sort_order == "遞增")
            work_df = work_df.sort_values(by='品名', ascending=is_ascending).head(50)

            if not work_df.empty:
                st.caption(f"找到 {len(work_df)} 筆結果")
                for _, row in work_df.iterrows():
                    bc_val = row.get('條碼', '')
                    has_image = '圖片' in row and str(row['圖片']).startswith('http')
                    
                    with st.container(border=True): # 增加框線感，適合手機閱讀
                        c1, c2 = st.columns([1, 2])
                        with c1:
                            if bc_val:
                                st.image(f"https://bwipjs-api.metafloor.com/?bcid=code128&text={bc_val}&scale=2&includetext", use_container_width=True)
                            else:
                                st.write("無條碼")
                        with c2:
                            st.subheader(row['品名'])
                            st.write(f"代號: `{row.get('商品代號', '-')}`")
                            if has_image:
                                with st.expander("查看商品圖"):
                                    st.image(row['圖片'], use_container_width=True)
            else:
                st.warning("查無資料")
        else:
            st.info("請輸入關鍵字或選擇類別開始搜尋")
            st.metric("資料庫總品項", len(df_main))

    # --- Tab 2: 新增商品 ---
    with tab_add:
        st.header("新增資料至試算表")
        type_options = unique_types + ["➕ 新增其他類別..."]
        chosen_type = st.selectbox("選擇類別", type_options, key="add_type")
        final_type = st.text_input("新類別名稱") if chosen_type == "➕ 新增其他類別..." else chosen_type
        
        new_name = st.text_input("商品品名 (必填)")
        new_bc = st.text_input("商品條碼 (必填)", placeholder="請輸入條碼數字")
        
        if st.button("🚀 確認送出資料", use_container_width=True):
            if final_type and new_name and new_bc:
                payload = {"type": final_type, "name": new_name, "barcode": new_bc}
                try:
                    res = requests.post(SCRIPT_URL, data=json.dumps(payload))
                    if "Success" in res.text:
                        st.success("✅ 寫入成功！請重新整理頁面。")
                        st.cache_data.clear()
                    else: 
                        st.error(f"❌ 寫入失敗: {res.text}")
                except: 
                    st.error("❌ 無法連線至 Google Apps Script")
            else: 
                st.warning("請完整填寫類別、品名與條碼")

    # --- Tab 3: 系統設定 (原側邊欄滑桿) ---
    with tab_settings:
        st.header("顯示設定")
        st.write("調整畫面顯示效果")
        # 這裡可以放原本 sidebar 的調整功能
        if st.button("♻️ 強制重新整理資料"):
            st.cache_data.clear()
            st.rerun()

else:
    st.error("資料載入失敗，請檢查來源網址。")
