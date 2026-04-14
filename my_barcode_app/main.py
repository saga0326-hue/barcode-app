import streamlit as st
import pandas as pd
import os

# 1. 網頁設定
st.set_page_config(page_title="專業商品雲端管理系統", layout="wide", page_icon="📦")

# 2. 強化版讀取函式
@st.cache_data(ttl=60)
def fetch_data(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        df = pd.read_csv(url, dtype=str, storage_options=headers)
        df.columns = df.columns.str.strip() # 自動去除欄位前後空格
        return df
    except Exception as e:
        return f"連線錯誤: {e}"

# 3. 取得 Secrets 網址
try:
    DATA_URL = st.secrets["data_url"]
    CAT_URL = st.secrets["cat_url"]
except:
    st.error("❌ Secrets 設定有誤，請確認 data_url 與 cat_url 是否正確。")
    st.stop()

st.title("🛡️ 團隊共享：雲端商品管理系統")
st.markdown("---")

# 讀取資料
df = fetch_data(DATA_URL)
df_cat = fetch_data(CAT_URL)

# --- 側邊欄控制區 ---
st.sidebar.header("🔍 篩選與設定")
img_size = st.sidebar.slider("條碼與圖片大小", 50, 250, 120, 10)

# 【下拉選單：依據你的「類型」欄位】
selected_type = "全部"
if isinstance(df_cat, pd.DataFrame) and '類型' in df_cat.columns:
    unique_types = df_cat['類型'].dropna().unique().tolist()
    cat_list = ["全部"] + sorted([str(t) for t in unique_types if str(t) != 'nan'])
    selected_type = st.sidebar.selectbox("📂 常用類型快選", cat_list)
else:
    st.sidebar.warning("⚠️ 分類表載入中或『類型』欄位名稱不符")

search_name = st.sidebar.text_input("品名搜尋")
search_code = st.sidebar.text_input("條碼/代號搜尋")

# --- 主畫面顯示邏輯 ---
if isinstance(df, pd.DataFrame):
    filtered_df = df.copy()

    # A. 類型過濾 (使用你的欄位：類型、條碼商品)
    if selected_type != "全部" and isinstance(df_cat, pd.DataFrame):
        if '條碼商品' in df_cat.columns:
            target_barcodes = df_cat[df_cat['類型'] == selected_type]['條碼商品'].unique().tolist()
            filtered_df = filtered_df[filtered_df['條碼商品'].isin(target_barcodes)]

    # B. 文字搜尋 (使用你的欄位：品名、條碼商品、代號)
    if search_name and '品名' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['品名'].str.contains(search_name, na=False)]
    
    if search_code:
        # 同時搜尋「條碼商品」與「代號」
        mask = pd.Series([False] * len(filtered_df), index=filtered_df.index)
        if '條碼商品' in filtered_df.columns:
            mask |= filtered_df['條碼商品'].str.contains(search_code, na=False)
        if '代號' in filtered_df.columns:
            mask |= filtered_df['代號'].str.contains(search_code, na=False)
        filtered_df = filtered_df[mask]

    # C. 顯示結果
    if search_name or search_code or selected_type != "全部":
        st.success(f"找到 {len(filtered_df)} 筆符合條件的商品")
        
        # 圖片資料夾設定
        current_dir = os.path.dirname(os.path.abspath(__file__))
        IMAGE_FOLDER = os.path.abspath(os.path.join(current_dir, "..", "images"))

        for _, row in filtered_df.head(50).iterrows():
            # 依據你的欄位名稱讀取資料
            bc_val = str(row.get('條碼商品', '')).replace('*', '').strip()
            item_id = str(row.get('代號', 'unknown'))
            
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
                    # 優先嘗試你的「圖片」欄位 URL，若無則找 local
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
        st.info("💡 請在左側輸入搜尋條件。")
        st.metric("雲端資料總數", len(df))
else:
    st.error(f"❌ 雲端資料庫連線失敗: {df}")
