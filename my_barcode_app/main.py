import streamlit as st
import pandas as pd
import requests
import json

# 1. 基本頁面設定 (手機優先配置)
st.set_page_config(page_title="專業商品條碼系統", layout="wide", page_icon="📦")

# 2. 強化版讀取函式：含資料清理與快取
@st.cache_data(ttl=60)
def fetch_data(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        # 讀取並強制轉為字串處理，避免科學記號
        df = pd.read_csv(url, dtype=str, storage_options=headers)
        df.columns = df.columns.str.strip()
        # 技術細節：清理所有欄位的空格與特殊星號
        df = df.apply(lambda x: x.str.strip().str.replace('*', '', regex=False) if isinstance(x, str) else x)
        return df
    except Exception as e:
        return f"ERROR: {str(e)}"

# 3. 取得網址 (從 streamlit/secrets.toml 抓取)
try:
    DATA_URL = st.secrets["data_url"]
    CAT_URL = st.secrets["cat_url"]
    SCRIPT_URL = st.secrets.get("script_url", "")
except Exception:
    st.error("❌ 請先在 secrets.toml 中設定 data_url, cat_url 與 script_url")
    st.stop()

st.title("🛡️ 團隊共享：條碼系統")

df_main = fetch_data(DATA_URL)
df_cat = fetch_data(CAT_URL)

# --- 側邊欄控制區 ---
st.sidebar.header("🔍 篩選與設定")
img_size = st.sidebar.slider("圖片/條碼顯示大小", 50, 300, 150, 10)
sort_order = st.sidebar.radio("排序方式", ["品名遞增 (A-Z)", "品名遞減 (Z-A)"])

# 取得現有類別清單
unique_types = []
if isinstance(df_cat, pd.DataFrame) and '類型' in df_cat.columns:
    unique_types = sorted([str(t) for t in df_cat['類型'].dropna().unique() if str(t) != 'nan' and str(t) != ''])

# 查詢模式的分類選單
selected_type = st.sidebar.selectbox("📂 常用類型快選", ["全部"] + unique_types)

search_name = st.sidebar.text_input("📝 品名搜尋")

# 優化 1：條碼搜尋改用數字輸入，自動喚起手機數字鍵盤
search_code_num = st.sidebar.number_input("🔢 條碼/代號搜尋", value=0, step=1, format="%d")
search_code = str(search_code_num) if search_code_num != 0 else ""

st.sidebar.markdown("---")

# --- 側邊欄：新增商品區 ---
st.sidebar.header("➕ 新增商品")
with st.sidebar.expander("展開填寫新資訊"):
    type_options = unique_types + ["➕ 新增其他類別..."]
    chosen_type = st.selectbox("選擇類別", type_options)
    
    final_type = ""
    if chosen_type == "➕ 新增其他類別...":
        final_type = st.text_input("請輸入新類別名稱")
    else:
        final_type = chosen_type
        
    new
