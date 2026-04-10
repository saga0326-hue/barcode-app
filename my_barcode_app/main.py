import streamlit as st
import pandas as pd
import os

# 1. 頁面基本設定
st.set_page_config(page_title="專業商品條碼檢索系統", layout="wide", page_icon="📦")

# 2. 檔案路徑設定
current_dir = os.path.dirname(os.path.abspath(__file__))
DATA_FILE_PATH = os.path.join(current_dir, "data.xlsx")
CAT_FILE_PATH = os.path.join(current_dir, "categories.xlsx")
# 圖片資料夾在上一層 (..) 的 images 裡
IMAGE_FOLDER = os.path.abspath(os.path.join(current_dir, "..", "images"))

@st.cache_data
def load_data(path):
    if os.path.exists(path):
        try:
            # 讀取 Excel 並強制轉為字串，避免 07 口座變成 7
            temp_df = pd.read_excel(path, dtype=str)
            # 關鍵：自動清除欄位名稱前後可能存在的隱形空格
            temp_df.columns = temp_df.columns.str.strip()
            return temp_df
        except Exception as e:
            st.error(f"讀取檔案失敗 ({os.path.basename(path)}): {e}")
    return None

st.title("🛡️ 團隊共享：商品稽核與影像系統")
st.markdown("---")

# 3. 載入資料
df = load_data(DATA_FILE_PATH)
df_cat = load_data(CAT_FILE_PATH)

if df is not None:
    # --- 側邊欄設計 ---
    st.sidebar.header("🔍 篩選與分類")
    
    # 4. 下拉選單邏輯
    selected_type = "全部"
    if df_cat is not None:
        # 檢查「類型」欄位是否存在
        if '類型' in df_cat.columns:
            # 取得不重複的類型清單
            unique_types = df_cat['類型'].dropna().unique().tolist()
            cat_list = ["全部"] + sorted(unique_types)
            selected_type = st.sidebar.selectbox("📂 常用類型快選", cat_list)
        else:
            st.sidebar.error("❌ 分類檔中找不到『類型』欄位")
            # 偵錯用：列出目前讀到的所有標題
            st.sidebar.write("目前偵測到的標題有：", list(df_cat.columns))
    else:
        st.sidebar.info("💡 尚未載入 categories.xlsx")

    # 手動搜尋欄位
    search_name = st.sidebar.text_input("品名搜尋", placeholder="關鍵字...")
    search_loc = st.sidebar.text_input("口座搜尋", placeholder="例如：07")
    search_code = st.sidebar.text_input("代號/條碼搜尋")

    # --- 5. 篩選邏輯 ---
    filtered_df = df.copy()
    
    # 如果選了特定類型
    if selected_type != "全部":
        if '商品代號' in df_cat.columns:
            target_ids = df_cat[df_cat['類型'] == selected_type]['商品代號'].tolist()
            filtered_df = filtered_df[filtered_df['商品代號'].isin(target_ids)]
        else:
            st.sidebar.warning("分類檔遺失『商品代號』欄位")

    # 關鍵字過濾
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
        
        # 限制顯示前 50 筆避免網頁過慢
        display_df = filtered_df.head(50)
        if count > 50:
            st.warning("結果過多，僅顯示前 50 筆。")

        for _, row in display_df.iterrows():
            clean_barcode = str(row['條碼']).strip('*')
            item_id = str(row['商品代號'])
            
            # 檢查圖片是否存在 (.jpg 或 .png)
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
                    # 使用 bwipjs 生成條碼
                    barcode_url = f"https://bwipjs-api.metafloor.com/?bcid=code128&text={clean_barcode}&scale=3&rotate=N&includetext"
                    st.image(barcode_url, caption="掃描用條碼", use_container_width=True)
                st.divider()
    else:
        st.info("💡 請在左側輸入關鍵字或從分類選單中點選。")
        st.metric("資料庫總品項數", len(df))
else:
    st.error("❌ 無法載入主資料檔 data.xlsx，請確認檔案路徑是否正確。")
