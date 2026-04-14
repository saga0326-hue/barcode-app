import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="專業商品雲端管理系統", layout="wide", page_icon="📦")

@st.cache_data(ttl=30) # 縮短快取時間以便偵錯
def fetch_data(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        df = pd.read_csv(url, dtype=str, storage_options=headers)
        df.columns = df.columns.str.strip()
        df = df.apply(lambda x: x.str.strip() if isinstance(x, str) else x)
        return df
    except Exception as e:
        # 回傳具體的錯誤訊息字串
        return f"ERROR: {str(e)}"

# 取得 Secrets
try:
    DATA_URL = st.secrets["data_url"]
    CAT_URL = st.secrets["cat_url"]
except:
    st.error("❌ Secrets 設定缺失")
    st.stop()

st.title("🛡️ 團隊共享：雲端商品管理系統")

# 讀取
df = fetch_data(DATA_URL)
df_cat = fetch_data(CAT_URL)

# --- 側邊欄 ---
st.sidebar.header("🔍 篩選與設定")

# 【分類選單偵錯邏輯】
selected_type = "全部"
if isinstance(df_cat, pd.DataFrame):
    if '類型' in df_cat.columns:
        unique_types = df_cat['類型'].dropna().unique().tolist()
        cat_list = ["全部"] + sorted([str(t) for t in unique_types if t])
        selected_type = st.sidebar.selectbox("📂 常用類型快選", cat_list)
    else:
        st.sidebar.error(f"❌ 欄位不符。目前欄位：{list(df_cat.columns)}")
else:
    # 這裡會直接把為什麼「載入中」的原因寫出來
    st.sidebar.error(f"⚠️ 分類表讀取失敗")
    st.sidebar.code(df_cat) # 顯示具體錯誤代碼 (如 401 或 404)

# --- 搜尋與顯示 (與之前邏輯一致) ---
search_name = st.sidebar.text_input("品名搜尋")
search_code = st.sidebar.text_input("條碼/代號搜尋")

if isinstance(df, pd.DataFrame):
    filtered_df = df.copy()
    
    # 類型篩選
    if selected_type != "全部" and isinstance(df_cat, pd.DataFrame):
        target_barcodes = df_cat[df_cat['類型'] == selected_type]['條碼'].unique().tolist()
        filtered_df = filtered_df[filtered_df['條碼'].isin(target_barcodes)]
    
    # 文字搜尋
    if search_name:
        filtered_df = filtered_df[filtered_df['品名'].str.contains(search_name, na=False)]
    if search_code:
        mask = (filtered_df['條碼'].str.contains(search_code, na=False) | 
                filtered_df['商品代號'].str.contains(search_code, na=False))
        filtered_df = filtered_df[mask]

    if search_name or search_code or selected_type != "全部":
        st.success(f"找到 {len(filtered_df)} 筆結果")
        # (顯示商品卡片邏輯...)
        for _, row in filtered_df.head(50).iterrows():
            st.write(f"品名: {row.get('品名')} | 口座: {row.get('口座')}")
            st.divider()
    else:
        st.metric("雲端總品項", len(df))
else:
    st.error(f"❌ 主資料讀取失敗: {df}")
