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
            # 讀取並強制轉為字串，自動清除前後空格
            temp_df = pd.read_excel(path, dtype=str)
            temp_df.columns = temp_df.columns.str.strip()
            for col in temp_df.columns:
                temp_df[col] = temp_df[col].str.strip()
            return temp_df
        except Exception as e:
            st.error(f"讀取檔案失敗: {e}")
    return None

st.title("🛡️ 團隊共享：商品稽核系統")
st.markdown("---")

df = load_data(DATA_FILE_PATH)
df_cat = load_data(CAT_FILE_PATH)

if df is not None:
    st.sidebar.header("🔍 篩選與分類")
    
    # 3. 下拉選單邏輯
    selected_type = "全部"
    if df_cat is not None:
        if '類型' in df_cat.columns:
            unique_types = df_cat['類型'].dropna().unique().tolist()
            cat_list = ["全部"] + sorted(unique_types)
            selected_type = st.sidebar.selectbox("📂 常用類型快選", cat_list)
        else:
            st.sidebar.error("❌ 分類檔中找不到『類型』欄位")

    search_name = st.sidebar.text_input("品名搜尋")
    search_loc = st.sidebar.text_input("口座搜尋")
    search_code = st.sidebar.text_input("條碼或代號關鍵字搜尋")

    # --- 4. 核心篩選邏輯 (改用條碼連結) ---
    filtered_df = df.copy()
    
    if selected_type != "全部":
        # 💡 改動：從分類檔抓取「條碼」清單
        if '條碼' in df_cat.columns:
            target_barcodes = df_cat[df_cat['類型'] == selected_type]['條碼'].dropna().unique().tolist()
            # 用「條碼」去主檔搜尋
            filtered_df = filtered_df[filtered_df['條碼'].isin(target_barcodes)]
            
            if len(filtered_df) == 0:
                st.sidebar.warning(f"⚠️ 分類檔有 {len(target_barcodes)} 筆條碼，但主檔中無匹配資料。")
        else:
            st.sidebar.error("❌ 分類檔缺少『條碼』欄位，無法連結資料。")

    # 關鍵字過濾
    if search_name:
        filtered_df = filtered_df[filtered_df['品名'].str.contains(search_name, na=False)]
    if search_loc:
        filtered_df = filtered_df[filtered_df['口座'].str.contains(search_loc, na=False)]
    if search_code:
        mask = (filtered_df['條碼'].str.contains(search_code, na=False) | 
                filtered_df['商品代號'].str.contains(search_code, na=False))
        filtered_df = filtered_df[mask]

    # --- 5. 顯示結果 ---
    if (selected_type != "全部") or search_name or search_loc or search_code:
        count = len(filtered_df)
        st.subheader(f"📊 檢索結果 (共 {count} 筆)")
        
        display_df = filtered_df.head(50)
        for _, row in display_df.iterrows():
            # 取得顯示用資料
            barcode_val = str(row.get('條碼', '')).replace('*', '').strip()
            item_id = str(row.get('商品代號', 'unknown')) # 💡 圖片抓取仍用商品代號
            
            with st.container():
                col_img, col_info, col_bc = st.columns([1.5, 2.5, 1.5])
                
                with col_img:
                    # 💡 以「商品代號」抓取圖片
                    img_found = False
                    if item_id != 'unknown' and item_id != 'nan':
                        for ext in ['.jpg', '.png', '.jpeg']:
                            path = os.path.join(IMAGE_FOLDER, f"{item_id}{ext}")
                            if os.path.exists(path):
                                st.image(path, use_container_width=True)
                                img_found = True
                                break
                    if not img_found:
                        st.image("https://via.placeholder.com/150?text=No+Photo", use_container_width=True)
                
                with col_info:
                    st.markdown(f"### {row.get('品名', '未命名')}")
                    st.write(f"**📍 口座：** `{row.get('口座', '-')}`")
                    st.write(f"**🆔 代號：** `{item_id}`")
                    st.write(f"**📂 類型：** `{row.get('類型', '-')}`")
                
                with col_bc:
                    if barcode_val and barcode_val != 'nan':
                        # 生成條碼圖片
                        barcode_url = f"https://bwipjs-api.metafloor.com/?bcid=code128&text={barcode_val}&scale=3&rotate=N&includetext"
                        st.image(barcode_url, caption="掃描條碼", use_container_width=True)
                st.divider()
    else:
        st.info("💡 請在左側選擇分類或輸入關鍵字。")
        st.metric("資料庫總品項數", len(df))
else:
    st.error("❌ 找不到主資料檔 data.xlsx")
