import streamlit as st
import pandas as pd
import os

# 1. 基本頁面設定
st.set_page_config(page_title="專業商品條碼系統", layout="wide", page_icon="📦")

# 2. 強化版讀取函式
@st.cache_data(ttl=60)
def fetch_data(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        df = pd.read_csv(url, dtype=str, storage_options=headers)
        # 清除標題與內容的所有前後空白
        df.columns = df.columns.str.strip()
        df = df.apply(lambda x: x.str.strip() if isinstance(x, str) else x)
        return df
    except Exception as e:
        return f"ERROR: {str(e)}"

# 3. 取得網址 (從 Secrets 抓取)
DATA_URL = st.secrets["data_url"]
CAT_URL = st.secrets["cat_url"]

# 修改後的標題
st.title("🛡️ 團隊共享：條碼系統")

df_main = fetch_data(DATA_URL)
df_cat = fetch_data(CAT_URL)

# --- 側邊欄控制區 ---
st.sidebar.header("🔍 篩選與設定")
img_size = st.sidebar.slider("圖片/條碼大小", 50, 300, 150, 10)
sort_order = st.sidebar.radio("排序方式", ["品名遞增 (A-Z)", "品名遞減 (Z-A)"])

# 建立常用類型快選選單
selected_type = "全部"
if isinstance(df_cat, pd.DataFrame) and '類型' in df_cat.columns:
    unique_types = df_cat['類型'].dropna().unique().tolist()
    cat_list = ["全部"] + sorted([str(t) for t in unique_types if str(t) != 'nan' and str(t) != ''])
    selected_type = st.sidebar.selectbox("📂 常用類型快選", cat_list)

search_name = st.sidebar.text_input("品名搜尋")
search_code = st.sidebar.text_input("條碼/代號搜尋")

# --- 核心邏輯：動態切換資料庫 ---
if isinstance(df_main, pd.DataFrame) and isinstance(df_cat, pd.DataFrame):
    
    # 決定基礎資料來源
    if selected_type == "全部":
        work_df = df_main.copy()
        source_label = "主資料庫 (Data)"
    else:
        # 切換至 Categories 資料庫並鎖定該類型
        work_df = df_cat[df_cat['類型'] == selected_type].copy()
        source_label = f"分類表 (Categories) - {selected_type}"

    # 執行關鍵字過濾
    if search_name:
        work_df = work_df[work_df['品名'].str.contains(search_name, na=False
