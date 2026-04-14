import streamlit as st
import pandas as pd
import os

# 1. 網頁設定
st.set_page_config(page_title="專業商品雲端管理系統", layout="wide", page_icon="📦")

# 2. 取得 Secrets 網址
try:
    DATA_URL = st.secrets["data_url"]
    CAT_URL = st.secrets["cat_url"]
except Exception as e:
    st.error("❌ Secrets 設定錯誤，請確認 data_url 與 cat_url 是否已填寫。")
    st.stop()

# 3. 超穩定讀取函式 (加入 User-Agent 破解 401 錯誤)
@st.cache_data(ttl=0)
def load_cloud_data(url):
    try:
        # 加上 storage_options 模擬一般瀏覽器存取
        df = pd.read_csv(
            url, 
            dtype=str, 
            storage_options={'User-Agent': 'Mozilla/5.0'}
        )
        # 清除欄位與資料的空白
        df.columns = df.columns.str.strip()
        df = df.apply(lambda x: x.str.strip() if isinstance(x, str) else x)
        return df
    except Exception as e:
        st.error(f"☁️ 雲端連線失敗: {e}")
        return None

# 4. 圖片路徑
current_dir = os.path.dirname(os.path.abspath(__file__))
IMAGE_FOLDER = os.path.abspath(os.path.join(current_dir, "..", "images"))

st.title("🛡️ 團隊共享：雲端商品管理系統")
st.markdown("---")

# 讀取資料
df = load_cloud_data(DATA_URL)
df_cat = load_cloud_data(CAT_URL)

if df is not None:
    # --- 側邊欄：篩選與設定 ---
    st.sidebar.header("🔍 篩選與設定")
    img_size = st.sidebar.slider("條碼與圖片大小", 50, 250, 120, 10)
    
    # 💡 修復下拉選單：從 categories 分頁抓取「類型」
    selected_type = "全部"
    if df_cat is not None and '類型' in df_cat.columns:
        unique_types = df_cat['類型'].dropna().unique().tolist()
        cat_list = ["全部"] + sorted([t for t in unique_types if t != 'nan'])
        selected_type = st.sidebar.selectbox("📂 常用類型快選", cat_list)

    search_name = st.sidebar.text_input("品名搜尋")
    search_loc = st.sidebar.text_input("口座搜尋")
    search_code = st.sidebar.text_input("條碼/代號關鍵字")

    # --- 篩選邏輯 ---
    filtered_df = df.copy()

    # 1. 處理類型快選 (透過條碼關聯)
    if selected_type != "全部" and '條碼' in df_cat.columns:
        target_barcodes = df_cat[df_cat['類型'] == selected_type]['條碼'].dropna().unique().tolist()
        filtered_df = filtered_df[filtered_df['條碼'].isin(target_barcodes)]

    # 2. 處理文字搜尋
    if search_name:
        filtered_df = filtered_df[filtered_df['品名'].str.contains(search_name, na=False)]
    if search_loc:
        filtered_df = filtered_df[filtered_df['口座'].str.contains(search_loc, na=False)]
    if search_code:
        mask = (filtered_df['條碼'].str.contains(search_code, na=False) | 
                filtered_df['商品代號'].str.contains(search_code, na=False))
        filtered_df = filtered_df[mask]

    # --- 顯示結果 ---
    if (selected_type != "全部") or search_name or search_loc or search_code:
        display_count = len(filtered_df)
        st.caption(f"找到 {display_count} 筆符合條件的商品")
        
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
        st.info("💡 請在左側輸入搜尋條件或選擇類型。")
        st.metric("雲端總品項", len(df))
else:
    st.warning("☁️ 正在連線至雲端資料庫，請稍候...")
