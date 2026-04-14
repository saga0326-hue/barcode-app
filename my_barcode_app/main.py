import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import os

# 1. 網頁基本設定
st.set_page_config(page_title="專業商品雲端管理系統", layout="wide", page_icon="📦")

# 2. 建立 Google Sheets 連接 (會自動讀取你在 Secrets 設定的網址)
conn = st.connection("gsheets", type=GSheetsConnection)

# 3. 資料讀取函式
@st.cache_data(ttl=0) # ttl=0 確保每次重新整理都會抓取雲端最新資料
def load_gs_data(worksheet_name):
    try:
        df = conn.read(worksheet=worksheet_name)
        # 強制轉換成字串並去除首尾空白，避免搜尋出錯
        df = df.astype(str).apply(lambda x: x.str.strip())
        return df
    except Exception as e:
        st.error(f"雲端讀取失敗，請檢查工作表名稱是否為 '{worksheet_name}': {e}")
        return None

# 4. 圖片路徑設定 (維持讀取 GitHub 上的 images 資料夾)
current_dir = os.path.dirname(os.path.abspath(__file__))
IMAGE_FOLDER = os.path.abspath(os.path.join(current_dir, "..", "images"))

st.title("🛡️ 團隊共享：雲端商品管理系統")
st.markdown("---")

# 設定分頁：檢索、新增、管理員模式
tab1, tab2, tab3 = st.tabs(["🔍 商品檢索", "➕ 新增商品", "⚙️ 管理員模式"])

# --- Tab 1: 商品檢索 (手機優化版) ---
with tab1:
    df = load_gs_data("data")
    df_cat = load_gs_data("categories")
    
    if df is not None:
        st.sidebar.header("🔍 篩選與設定")
        # 💡 手機適配：手動縮放拉桿
        img_size = st.sidebar.slider("條碼與圖片大小", 50, 250, 120, 10)
        
        selected_type = "全部"
        if df_cat is not None and '類型' in df_cat.columns:
            cat_list = ["全部"] + sorted(df_cat['類型'].dropna().unique().tolist())
            selected_type = st.sidebar.selectbox("📂 常用類型快選", cat_list)

        search_name = st.sidebar.text_input("品名搜尋")
        search_loc = st.sidebar.text_input("口座搜尋")
        search_code = st.sidebar.text_input("條碼/代號搜尋")

        # 篩選邏輯
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

        # 顯示結果
        if (selected_type != "全部") or search_name or search_loc or search_code:
            display_df = filtered_df.head(50)
            for _, row in display_df.iterrows():
                bc_val = str(row.get('條碼', '')).replace('*', '').strip()
                item_id = str(row.get('商品代號', 'unknown'))
                
                with st.container():
                    # 手機端 1:3:1 排版
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
            st.info("💡 請從左側選單開始搜尋。")
            st.metric("雲端資料總數", len(df))

# --- Tab 2: 新增商品 ---
with tab2:
    st.subheader("📝 提交新商品到雲端資料庫")
    with st.form("add_product_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            new_name = st.text_input("📦 商品品名 *")
            new_barcode = st.text_input("🔢 條碼 (Barcode) *")
            new_type = st.text_input("📂 商品類型")
        with c2:
            new_item_id = st.text_input("🆔 商品代號 (對應圖片檔名) *")
            new_loc = st.text_input("📍 口座位置")
        
        st.markdown("---")
        if st.form_submit_button("✅ 儲存並同步至 Google Sheets"):
            if new_name and new_barcode and new_item_id:
                # 讀取舊資料並串接新資料
                old_df = load_gs_data("data")
                new_row = pd.DataFrame([{
                    "類型": new_type, "品名": new_name, 
                    "條碼": new_barcode, "商品代號": new_item_id, "口座": new_loc
                }])
                final_df = pd.concat([old_df, new_row], ignore_index=True)
                
                # 寫回雲端
                conn.update(worksheet="data", data=final_df)
                st.cache_data.clear() # 清除快取以便立即搜到新資料
                st.success(f"🎊 商品「{new_name}」已同步成功！")
                st.balloons()
            else:
                st.error("❌ 請填寫必填欄位 (*)")

# --- Tab 3: 管理員模式 (維護與備份) ---
with tab3:
    st.subheader("🔐 資料管理與維護")
    admin_pwd = st.text_input("請輸入管理員密碼", type="password")
    if admin_pwd == "7410":
        st.success("✅ 管理員權限已開啟")
        st.info("在此模式下，您可以直接檢視雲端原始表格，或進行備份。")
        raw_df = load_gs_data("data")
        st.dataframe(raw_df)
        
        # 匯出備份功能
        csv = raw_df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 下載雲端資料備份 (CSV)", data=csv, file_name="backup_data.csv", mime="text/csv")
    elif admin_pwd != "":
        st.error("❌ 密碼錯誤")
