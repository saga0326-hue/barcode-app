import streamlit as st
import pandas as pd
import os

# 1. 基本設定
st.set_page_config(page_title="專業商品雲端管理系統", layout="wide", page_icon="📦")

# 2. 定義讀取函式 (強化模擬瀏覽器行為)
@st.cache_data(ttl=60) # 每分鐘自動更新一次
def fetch_data(url):
    try:
        # 使用最新的瀏覽器標頭，防止 Google 阻擋
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        df = pd.read_csv(url, dtype=str, storage_options=headers)
        # 清除資料中的空格與換行
        df.columns = df.columns.str.strip()
        df = df.apply(lambda x: x.str.strip() if isinstance(x, str) else x)
        return df
    except Exception as e:
        return f"Error: {e}"

# 3. 取得網址 (從 Secrets 抓取)
DATA_URL = st.secrets["data_url"]
CAT_URL = st.secrets["cat_url"]

st.title("🛡️ 團隊共享：雲端商品管理系統")
st.markdown("---")

# 4. 讀取雲端資料
df = fetch_data(DATA_URL)
df_cat = fetch_data(CAT_URL)

# --- 側邊欄控制區 ---
st.sidebar.header("🔍 篩選與設定")
img_size = st.sidebar.slider("條碼與圖片大小", 50, 250, 120, 10)

# 處理下拉選單
selected_type = "全部"
if isinstance(df_cat, pd.DataFrame) and '類型' in df_cat.columns:
    unique_types = df_cat['類型'].dropna().unique().tolist()
    cat_list = ["全部"] + sorted([str(t) for t in unique_types if str(t) != 'nan'])
    selected_type = st.sidebar.selectbox("📂 常用類型快選", cat_list)
else:
    st.sidebar.warning("⚠️ 分類選單載入中或發生錯誤")

search_name = st.sidebar.text_input("品名搜尋")
search_code = st.sidebar.text_input("條碼/代號搜尋")

# --- 主畫面顯示邏輯 ---
if isinstance(df, pd.DataFrame):
    filtered_df = df.copy()

    # A. 類型過濾 (透過 Categories 表關聯)
    if selected_type != "全部" and isinstance(df_cat, pd.DataFrame):
        target_barcodes = df_cat[df_cat['類型'] == selected_type]['條碼'].unique().tolist()
        filtered_df = filtered_df[filtered_df['條碼'].isin(target_barcodes)]

    # B. 文字搜尋
    if search_name:
        filtered_df = filtered_df[filtered_df['品名'].str.contains(search_name, na=False)]
    if search_code:
        mask = (filtered_df['條碼'].str.contains(search_code, na=False) | 
                filtered_df['商品代號'].str.contains(search_code, na=False))
        filtered_df = filtered_df[mask]

    # C. 顯示結果
    if search_name or search_code or selected_type != "全部":
        st.success(f"找到 {len(filtered_df)} 筆符合條件的商品")
        
        # 圖片資料夾設定
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
                    st.caption(f"口座: {row.get('口座', '-')} | 代號: {item_id}")
                with col_img:
                    img_found = False
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
        st.metric("雲端資料總數", len(df))
else:
    st.error(f"❌ 雲端資料庫連線失敗，請稍後再試。\n錯誤訊息: {df}")
