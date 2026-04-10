import streamlit as st
import pandas as pd
import os

# 1. 頁面基本設定
st.set_page_config(page_title="專業商品條碼檢索系統", layout="wide", page_icon="📦")

# 2. 檔案路徑設定 (針對你的資料夾結構優化)
current_dir = os.path.dirname(os.path.abspath(__file__))
# 你的 Excel 檔案就在 main.py 旁邊
DATA_FILE_PATH = os.path.join(current_dir, "data.xlsx")
CAT_FILE_PATH = os.path.join(current_dir, "categories.xlsx")
# 💡 重點：圖片資料夾在上一層 (..) 的 images 裡
IMAGE_FOLDER = os.path.abspath(os.path.join(current_dir, "..", "images"))

@st.cache_data
def load_data(path):
    if os.path.exists(path):
        try:
            return pd.read_excel(path, dtype=str)
        except Exception as e:
            st.error(f"讀取 {os.path.basename(path)} 失敗: {e}")
    return None

st.title("🛡️ 團隊共享：商品條碼與影像系統")
st.caption("同步支援：分類快選 / 關鍵字搜尋 / 自動條碼生成 / 商品圖對照")
st.markdown("---")

# 3. 載入資料
df = load_data(DATA_FILE_PATH)
df_cat = load_data(CAT_FILE_PATH)

if df is not None:
    # --- 側邊欄設計 ---
    st.sidebar.header("🔍 篩選與分類")
    
    # 下拉選單功能
    selected_type = "全部"
    if df_cat is not None:
        cat_list = ["全部"] + sorted(df_cat['類型'].unique().tolist())
        selected_type = st.sidebar.selectbox("📂 常用類型快選", cat_list)
    else:
        st.sidebar.info("💡 如需分類功能，請檢查 categories.xlsx")

    search_name = st.sidebar.text_input("品名搜尋", placeholder="關鍵字...")
    search_loc = st.sidebar.text_input("口座搜尋", placeholder="例如：07")
    search_code = st.sidebar.text_input("代號/條碼搜尋")

    # --- 篩選邏輯 ---
    filtered_df = df.copy()
    
    # 類別連動：先從分類檔找出代號，再回主檔過濾
    if selected_type != "全部":
        target_ids = df_cat[df_cat['類型'] == selected_type]['商品代號'].tolist()
        filtered_df = filtered_df[filtered_df['商品代號'].isin(target_ids)]

    if search_name:
        filtered_df = filtered_df[filtered_df['品名'].str.contains(search_name, na=False)]
    if search_loc:
        filtered_df = filtered_df[filtered_df['口座'].str.contains(search_loc, na=False)]
    if search_code:
        mask = (filtered_df['條碼'].str.contains(search_code, na=False) | 
                filtered_df['商品代號'].str.contains(search_code, na=False))
        filtered_df = filtered_df[mask]

    # --- 顯示結果 ---
    # 判斷使用者是否有操作搜尋
    has_filter = (selected_type != "全部") or search_name or search_loc or search_code

    if has_filter:
        count = len(filtered_df)
        st.subheader(f"📊 檢索結果 (共 {count} 筆)")
        
        display_df = filtered_df.head(50)
        if count > 50:
            st.warning("結果過多，僅顯示前 50 筆，請增加篩選條件。")

        for _, row in display_df.iterrows():
            clean_barcode = str(row['條碼']).strip('*')
            item_id = str(row['商品代號'])
            
            # 圖片路徑判斷 (支援 .jpg 或 .png)
            img_path_jpg = os.path.join(IMAGE_FOLDER, f"{item_id}.jpg")
            img_path_png = os.path.join(IMAGE_FOLDER, f"{item_id}.png")
            
            with st.container():
                col_img, col_info, col_bc = st.columns([1.5, 2.5, 1.5])
                
                with col_img:
                    if os.path.exists(img_path_jpg):
                        st.image(img_path_jpg, use_container_width=True)
                    elif os.path.exists(img_path_png):
                        st.image(img_path_png, use_container_width=True)
                    else:
                        st.image("https://via.placeholder.com/150?text=No+Photo", use_container_width=True)
                
                with col_info:
                    st.markdown(f"### {row['品名']}")
                    st.write(f"**📍 口座：** `{row['口座']}`")
                    st.write(f"**🆔 代號：** `{item_id}`")
                    st.write(f"**🔢 條碼：** `{row['條碼']}`")
                
                with col_bc:
                    # 條碼生成 API
                    barcode_url = f"https://bwipjs-api.metafloor.com/?bcid=code128&text={clean_barcode}&scale=3&rotate=N&includetext"
                    st.image(barcode_url, caption="可直接掃描", use_container_width=True)
                st.divider()
    else:
        # 初始狀態：顯示統計數據
        st.info("💡 請在左側輸入關鍵字或從「常用類型」中選擇。")
        c1, c2 = st.columns(2)
        c1.metric("📦 資料庫總品項", len(df))
        if df_cat is not None:
            c2.metric("📂 已設定類別數", len(df_cat['類型'].unique()))
        
        # 顯示最後讀取路徑供開發者確認
        with st.expander("系統路徑檢查"):
            st.write(f"主程式路徑: `{current_dir}`")
            st.write(f"預計圖片路徑: `{IMAGE_FOLDER}`")
else:
    st.error("❌ 無法載入主資料檔 data.xlsx，請檢查 GitHub 檔案位置。")
