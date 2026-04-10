import streamlit as st
import pandas as pd
import os

# 1. 頁面基本設定
st.set_page_config(page_title="專業商品條碼檢索系統", layout="wide", page_icon="📦")

# 2. 檔案路徑設定
current_dir = os.path.dirname(os.path.abspath(__file__))
DATA_FILE_PATH = os.path.join(current_dir, "data.xlsx")
CAT_FILE_PATH = os.path.join(current_dir, "categories.xlsx")
# 圖片資料夾在上一層的 images 裡
IMAGE_FOLDER = os.path.abspath(os.path.join(current_dir, "..", "images"))

@st.cache_data
def load_data(path):
    if os.path.exists(path):
        try:
            temp_df = pd.read_excel(path, dtype=str)
            # 自動去除欄位名稱前後的空格
            temp_df.columns = temp_df.columns.str.strip()
            return temp_df
        except Exception as e:
            st.error(f"讀取 {os.path.basename(path)} 失敗: {e}")
    return None

st.title("🛡️ 團隊共享：條碼與影像")
st.markdown("---")

# 3. 載入資料
df = load_data(DATA_FILE_PATH)
df_cat = load_data(CAT_FILE_PATH)

if df is not None:
    # --- 側邊欄設計 ---
    st.sidebar.header("🔍 篩選與分類")
    
    # 4. 下拉選單邏輯 (強制校正版)
    selected_type = "全部"
    if df_cat is not None:
        # 💡 強力校正：如果找不到「類型」標題，強制把第一欄定義為類型，第二欄為代號
        if '類型' not in df_cat.columns:
            df_cat.rename(columns={df_cat.columns[0]: '類型', df_cat.columns[1]: '商品代號'}, inplace=True)
        
        # 取得類型清單
        cat_list = ["全部"] + sorted(df_cat['類型'].dropna().unique().tolist())
        selected_type = st.sidebar.selectbox("📂 常用類型快選", cat_list)
    else:
        st.sidebar.info("💡 尚未載入 categories.xlsx")

    search_name = st.sidebar.text_input("品名搜尋", placeholder="關鍵字...")
    search_loc = st.sidebar.text_input("口座搜尋", placeholder="例如：07")
    search_code = st.sidebar.text_input("代號/條碼搜尋")

    # --- 5. 篩選邏輯 ---
    filtered_df = df.copy()
    
    # 類別連動邏輯
    if selected_type != "全部":
        # 找出分類檔中屬於該類型的商品代號
        target_ids = df_cat[df_cat['類型'] == selected_type]['商品代號'].tolist()
        # 回到主檔過濾
        filtered_df = filtered_df[filtered_df['商品代號'].isin(target_ids)]

    if search_name:
        filtered_df = filtered_df[filtered_df['品名'].str.contains(search_name, na=False)]
    if search_loc:
        filtered_df = filtered_df[filtered_df['口座'].str.contains(search_loc, na=False)]
    if search_code:
        mask = (filtered_df['條碼'].str.contains(search_code, na=False) | 
                filtered_df['商品代號'].str.contains(search_code, na=False))
        filtered_df = filtered_df[mask]

    # --- 6. 顯示結果 ---
    has_filter = (selected_type != "全部") or search_name or search_loc or search_code

    if has_filter:
        count = len(filtered_df)
        st.subheader(f"📊 檢索結果 (共 {count} 筆)")
        
        display_df = filtered_df.head(50)
        for _, row in display_df.iterrows():
            clean_barcode = str(row['條碼']).strip('*')
            item_id = str(row['商品代號'])
            
            # 支援 .jpg 與 .png 圖片格式
            img_path_jpg = os.path.join(IMAGE_FOLDER, f"{item_id}.jpg")
            img_path_png = os.path.join(IMAGE_FOLDER, f"{item_
