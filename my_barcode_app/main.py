import streamlit as st
import pandas as pd
import os

# 1. 基本設定
st.set_page_config(page_title="專業商品雲端管理系統", layout="wide", page_icon="📦")

# 2. 強化版讀取函式 (模擬瀏覽器特徵)
@st.cache_data(ttl=60)
def fetch_data(url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
        }
        df = pd.read_csv(url, dtype=str, storage_options=headers)
        # 自動校正：清除標題與內容的前後空白
        df.columns = df.columns.str.strip()
        df = df.apply(lambda x: x.str.strip() if isinstance(x, str) else x)
        return df
    except Exception as e:
        return f"連線錯誤: {e}"

# 3. 取得網址 (從 Secrets 抓取)
try:
    DATA_URL = st.secrets["data_url"]
    CAT_URL = st.secrets["cat_url"]
except:
    st.error("❌ Secrets 設定缺失，請檢查 data_url 與 cat_url")
    st.stop()

st.title("🛡️ 團隊共享：雲端商品管理系統")
st.markdown("---")

# 讀取雲端資料
df = fetch_data(DATA_URL)
df_cat = fetch_data(CAT_URL)

# --- 側邊欄控制區 ---
st.sidebar.header("🔍 篩選與設定")
img_size = st.sidebar.slider("圖片/條碼大小", 50, 250, 120, 10)

# 【下拉選單邏輯：使用你提供的六個欄位之一「類型」】
selected_type = "全部"
if isinstance(df_cat, pd.DataFrame):
    if '類型' in df_cat.columns:
        unique_types = df_cat['類型'].dropna().unique().tolist()
        cat_list = ["全部"] + sorted([str(t) for t in unique_types if str(t) != 'nan' and str(t) != ''])
        selected_type = st.sidebar.selectbox("📂 常用類型快選", cat_list)
    else:
        # 如果找不到「類型」欄位，列出目前的欄位名稱幫你檢查
        st.sidebar.error(f"❌ 分類表找不到『類型』欄位\n目前欄位有: {list(df_cat.columns)}")
else:
    st.sidebar.warning(f"⚠️ 分類選單載入中...")

search_name = st.sidebar.text_input("品名搜尋")
search_code = st.sidebar.text_input("條碼/代號關鍵字")

# --- 主畫面顯示邏輯 ---
if isinstance(df, pd.DataFrame):
    filtered_df = df.copy()

    # A. 類型過濾 (直接從 categories 工作表過濾)
    if selected_type != "全部" and isinstance(df_cat, pd.DataFrame):
        # 只要 categories 表有「類型」和「條碼」，我們就用條碼來過濾主表
        if '條碼' in df_cat.columns:
            target_barcodes = df_cat[df_cat['類型'] == selected_type]['條碼'].unique().tolist()
            filtered_df = filtered_df[filtered_df['條碼'].isin(target_barcodes)]

    # B. 文字搜尋 (對應你的欄位：品名、條碼、商品代號)
    if search_name and '品名' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['品名'].str.contains(search_name, na=False)]
    
    if search_code:
        mask = pd.Series([False] * len(filtered_df), index=filtered_df.index)
        if '條碼' in filtered_df.columns:
            mask |= filtered_df['條碼'].str.contains(search_code, na=False)
        if '商品代號' in filtered_df.columns:
            mask |= filtered_df['商品代號'].str.contains(search_code, na=False)
        filtered_df = filtered_df[mask]

    # C. 顯示結果
    if search_name or search_code or selected_type != "全部":
        st.success(f"找到 {len(filtered_df)} 筆結果")
        
        current_dir = os.path.dirname(os.path.abspath(__file__))
        IMAGE_FOLDER = os.path.abspath(os.path.join(current_dir, "..", "images"))

        for _, row in filtered_df.head(50).iterrows():
            bc_val = str(row.get('條碼', '')).replace('*', '').strip()
            item_id = str(row.get('商品代號', 'unknown'))
            
            with st.container():
                col_bc, col_info, col_img = st.columns([1, 3, 1])
                with col_bc:
                    if bc_val and bc_val != 'nan':
                        bc_api = f"https://bwipjs-api.metafloor.com/?bcid=code128&text={bc_val}&scale=2&rotate=N&includetext"
                        st.image(bc_api, width=img_size)
                with col_info:
                    st.markdown(f"**{row.get('品名', '未命名')}**")
                    # 顯示你的欄位資訊
                    st.caption(f"口座: {row.get('口座', '-')} | 代號: {item_id}")
                with col_img:
                    img_found = False
                    # 優先顯示你的『圖片』欄位 (若是網址)
                    img_url = row.get('圖片', '')
                    if isinstance(img_url, str) and img_url.startswith('http'):
                        st.image(img_url, width=img_size)
                        img_found = True
                    else:
                        for ext in ['.jpg', '.png', '.jpeg']:
                            path = os.path.join(IMAGE_FOLDER, f"{item_id}{ext}")
                            if os.path.exists(path):
                                st.image(path, width=img_size)
                                img_found = True
                                break
                    if not img_found:
                        st.image("https://via.placeholder.com/100?text=No+Img", width=img_size)
            st.divider()
    else:
        st.info("💡 請在左側輸入搜尋條件或選擇常用類型。")
        # 顯示你目前的總品項數
        st.metric("雲端資料庫總品項", len(df))
else:
    st.error(f"❌ 資料載入失敗，訊息: {df}")
