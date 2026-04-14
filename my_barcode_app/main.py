import streamlit as st
import pandas as pd
import os

# 1. 網頁設定
st.set_page_config(page_title="專業商品雲端管理系統", layout="wide", page_icon="📦")

# 2. 讀取 Secrets 裡的 CSV 網址
# 這裡會對應你在 Secrets 貼上的 data_url 和 cat_url
try:
    DATA_URL = st.secrets["data_url"]
    CAT_URL = st.secrets["cat_url"]
except Exception as e:
    st.error("❌ Secrets 設定錯誤，請確認 data_url 與 cat_url 是否已填寫。")
    st.stop()

# 3. 讀取函式 (TTL=0 確保即時更新)
@st.cache_data(ttl=0)
def load_cloud_data(url):
    try:
        # 這裡直接讀取 Google 發布的 CSV 連結
        df = pd.read_csv(url, dtype=str)
        df.columns = df.columns.str.strip()
        df = df.apply(lambda x: x.str.strip() if isinstance(x, str) else x)
        return df
    except Exception as e:
        st.error(f"☁️ 雲端連線失敗: {e}")
        return None

# 4. 圖片路徑
current_dir = os.path.dirname(os.path.abspath(__file__))
IMAGE_FOLDER = os.path.abspath(os.path.join(current_dir, "..", "images"))

st.title("🛡️ 團隊共享：雲端商品條碼系統")
st.markdown("---")

# 讀取資料
df = load_cloud_data(DATA_URL)
df_cat = load_cloud_data(CAT_URL)

if df is not None:
    # --- 搜尋介面 ---
    st.sidebar.header("🔍 篩選與設定")
    img_size = st.sidebar.slider("條碼與圖片大小", 50, 250, 120, 10)
    
    # 品名、口座、關鍵字搜尋
    search_name = st.sidebar.text_input("品名搜尋")
    search_loc = st.sidebar.text_input("口座搜尋")
    search_code = st.sidebar.text_input("條碼/代號關鍵字")

    # 執行篩選
    filtered_df = df.copy()
    if search_name:
        filtered_df = filtered_df[filtered_df['品名'].str.contains(search_name, na=False)]
    if search_loc:
        filtered_df = filtered_df[filtered_df['口座'].str.contains(search_loc, na=False)]
    if search_code:
        mask = (filtered_df['條碼'].str.contains(search_code, na=False) | 
                filtered_df['商品代號'].str.contains(search_code, na=False))
        filtered_df = filtered_df[mask]

    # --- 顯示結果 ---
    if search_name or search_loc or search_code:
        for _, row in filtered_df.head(50).iterrows():
            bc_val = str(row.get('條碼', '')).replace('*', '').strip()
            item_id = str(row.get('商品代號', 'unknown'))
            
            with st.container():
                col_bc, col_info, col_img = st.columns([1, 3, 1])
                with col_bc:
                    if bc_val and bc_val != 'nan':
                        url = f"https://bwipjs-api.metafloor.com/?bcid=code128&text={bc_val}&scale=2&rotate=N&includetext"
                        st.image(url, width=img_size)
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
        st.info("💡 請在左側輸入搜尋條件。")
        st.metric("雲端總品項", len(df))
else:
    st.warning("等待雲端資料載入中...")
