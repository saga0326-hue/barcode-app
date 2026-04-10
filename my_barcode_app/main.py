import streamlit as st
import pandas as pd
import os

# 1. 基本設定
st.set_page_config(page_title="專業商品條碼檢索系統", layout="wide", page_icon="📦")

# 2. 路徑設定
current_dir = os.path.dirname(os.path.abspath(__file__))
DATA_FILE_PATH = os.path.join(current_dir, "data.xlsx")
CAT_FILE_PATH = os.path.join(current_dir, "categories.xlsx")
IMAGE_FOLDER = os.path.abspath(os.path.join(current_dir, "..", "images"))

@st.cache_data
def load_data(path):
    if os.path.exists(path):
        try:
            temp_df = pd.read_excel(path, dtype=str)
            temp_df.columns = temp_df.columns.str.strip()
            for col in temp_df.columns:
                temp_df[col] = temp_df[col].str.strip()
            return temp_df
        except Exception as e:
            st.error(f"讀取失敗: {e}")
    return None

st.title("🛡️ 團隊共享：商品稽核系統")
st.markdown("---")

df = load_data(DATA_FILE_PATH)
df_cat = load_data(CAT_FILE_PATH)

if df is not None:
    # --- 側邊欄 ---
    st.sidebar.header("🔍 篩選與設定")
    
    # 💡 增加手動縮放功能
    st.sidebar.subheader("📱 行動裝置顯示調整")
    img_size = st.sidebar.slider("條碼與圖片大小", min_value=50, max_value=250, value=120, step=10)

    # 下拉選單
    selected_type = "全部"
    if df_cat is not None and '類型' in df_cat.columns:
        unique_types = df_cat['類型'].dropna().unique().tolist()
        cat_list = ["全部"] + sorted(unique_types)
        selected_type = st.sidebar.selectbox("📂 常用類型快選", cat_list)

    search_name = st.sidebar.text_input("品名搜尋")
    search_loc = st.sidebar.text_input("口座搜尋")
    search_code = st.sidebar.text_input("關鍵字搜尋")

    # --- 篩選邏輯 ---
    filtered_df = df.copy()
    if selected_type != "全部" and '條碼' in df_cat.columns:
        target_barcodes = df_cat[df_cat['類型'] == selected_type]['條碼'].dropna().unique().tolist()
        filtered_df = filtered_df[filtered_df['條碼'].isin(target_barcodes)]

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
        display_df = filtered_df.head(50)
        for _, row in display_df.iterrows():
            barcode_val = str(row.get('條碼', '')).replace('*', '').strip()
            item_id = str(row.get('商品代號', 'unknown'))
            
            with st.container():
                # 手機上使用 1:3:1 的緊湊比例
                col_bc, col_info, col_img = st.columns([1, 3, 1])
                
                with col_bc:
                    if barcode_val and barcode_val != 'nan':
                        barcode_url = f"https://bwipjs-api.metafloor.com/?bcid=code128&text={barcode_val}&scale=2&rotate=N&includetext"
                        # 💡 套用手動大小設定
                        st.image(barcode_url, width=img_size)
                
                with col_info:
                    st.markdown(f"**{row.get('品名', '未命名')}**")
                    st.caption(f"口座: {row.get('口座', '-')} | 代號: {item_id}")
                
                with col_img:
                    img_found = False
                    if item_id != 'unknown':
                        for ext in ['.jpg', '.png', '.jpeg']:
                            path = os.path.join(IMAGE_FOLDER, f"{item_id}{ext}")
                            if os.path.exists(path):
                                # 💡 套用手動大小設定
                                st.image(path, width=img_size)
                                img_found = True
                                break
                    if not img_found:
                        st.image("https://via.placeholder.com/100?text=No+Img", width=img_size)
                st.divider()
    else:
        st.info("💡 請從左側選單開始搜尋。")
else:
    st.error("❌ 找不到資料檔 data.xlsx")
