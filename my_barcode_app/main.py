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

# 2. 數據讀取與快取邏輯 (需求：TTL 改為 30)
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

df_main = fetch_data(DATA_URL)
df_cat = fetch_data(CAT_URL)

if isinstance(df_main, pd.DataFrame):
    # 手機版分頁設計
    tab_search, tab_add, tab_settings = st.tabs(["🔍 快速搜尋", "➕ 新增品項", "⚙️ 設定"])

    # --- Tab 3: 系統設定 (優先處理排序邏輯) ---
    with tab_settings:
        st.markdown("#### 🖼️ 顯示設定")
        img_size = st.slider("調整條碼/圖片大小", 50, 400, 150, 10)
        
        st.divider()
        st.markdown("#### 🔃 排序設定")
        # 需求：預設改為遞增 (index=0)
        sort_choice = st.radio("搜尋結果排序方式 (依品名)", ["遞增 (A-Z)", "遞減 (Z-A)"], index=0)
        is_ascending = True if sort_choice == "遞增 (A-Z)" else False
        
        st.divider()
        st.markdown("#### 🔄 數據維護")
        if st.button("強制重新整理資料庫", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    # --- Tab 1: 搜尋與顯示 ---
    with tab_search:
        unique_types = sorted([str(t) for t in df_cat['類型'].unique() if t and t != 'nan'])
        selected_type = st.selectbox("📂 選擇類別", ["全部"] + unique_types)

        search_name = st.text_input("📝 品名關鍵字", placeholder="輸入品名搜尋...")
        
        # 修正點：搜尋條碼改用 number_input 觸發數字鍵盤
        search_code_num = st.number_input("🔢 條碼/代號搜尋", step=1, value=None, placeholder="點擊輸入數字...")
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

            # 執行排序
            work_df = work_df.sort_values(by='品名', ascending=is_ascending).head(50)

            if not work_df.empty:
                st.caption(f"找到 {len(work_df)} 筆結果 (排序：{sort_choice})")
                for _, row in work_df.iterrows():
                    bc_val = row.get('條碼', '')
                    has_image = '圖片' in row and str(row['圖片']).startswith('http')
                    
                    with st.container(border=True):
                        c1, c2 = st.columns([1.5, 3])
                        with c1:
                            if bc_val:
