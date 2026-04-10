import streamlit as st
import pandas as pd
import os

# 1. 頁面基本設定
st.set_page_config(page_title="商品條碼分享系統", layout="wide", page_icon="📦")

# 2. 處理檔案路徑 (確保在雲端能找到隔壁的 data.xlsx)
# 取得目前 main.py 的路徑，並指向同資料夾下的 data.xlsx
current_dir = os.path.dirname(os.path.abspath(__file__))
DATA_FILE_PATH = os.path.join(current_dir, "data.xlsx")

# 3. 定義資料讀取函式
@st.cache_data
def load_data(source):
    """
    source 可以是路徑字串，也可以是 Streamlit 上傳的檔案對象
    """
    try:
        return pd.read_excel(source, dtype=str)
    except Exception as e:
        st.error(f"讀取檔案時發生錯誤: {e}")
        return None

st.title("🛡️ 團隊共享：商品條碼系統")
st.markdown("---")

# 4. 資料來源判定邏輯
df = None

# 優先檢查 GitHub 裡有沒有 data.xlsx
if os.path.exists(DATA_FILE_PATH):
    df = load_data(DATA_FILE_PATH)
    st.sidebar.success("✅ 已自動載入雲端資料庫 (data.xlsx)")
else:
    # 如果雲端沒檔案，才顯示上傳按鈕
    st.sidebar.warning("⚠️ 找不到預設資料檔，請手動上傳")
    uploaded_file = st.sidebar.file_uploader("上傳 Excel 檔案", type=["xlsx"])
    if uploaded_file:
        df = load_data(uploaded_file)

# 5. 主要運作邏輯
if df is not None:
    # 側邊欄搜尋控制
    st.sidebar.header("🔍 篩選條件")
    search_name = st.sidebar.text_input("品名搜尋", placeholder="例如：外套")
    search_loc = st.sidebar.text_input("口座搜尋", placeholder="例如：07")
    search_code = st.sidebar.text_input("代號/條碼搜尋", placeholder="輸入代號或條碼")

    # 判斷是否有搜尋行為
    has_search = search_name or search_loc or search_code

    if has_search:
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

        # 顯示結果
        count = len(filtered_df)
        st.subheader(f"📊 檢索結果 (共 {count} 筆)")

        if count == 0:
            st.warning("查無符合資料。")
        elif count > 50:
            st.warning("結果過多，僅顯示前 50 筆。")
            display_df = filtered_df.head(50)
        else:
            display_df = filtered_df

        # 產出卡片
        for _, row in display_df.iterrows():
            clean_barcode = str(row['條碼']).strip('*')
            with st.container():
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"### {row['品名']}")
                    st.write(f"📍 口座：`{row['口座']}` | 🆔 代號：`{row['商品代號']}`")
                    st.write(f"🔢 原始條碼：`{row['條碼']}`")
                with col2:
                    # 條碼生成
                    barcode_url = f"https://bwipjs-api.metafloor.com/?bcid=code128&text={clean_barcode}&scale=3&rotate=N&includetext"
                    st.image(barcode_url, use_container_width=True)
                st.divider()
    else:
        # 初始畫面
        st.info("💡 請在左側輸入關鍵字開始搜尋。")
        st.metric("資料庫商品總數", len(df))
        st.write(f"目前讀取路徑: `{DATA_FILE_PATH}`")
else:
    st.info("請確認 GitHub 儲存庫中是否包含 data.xlsx 檔案。")
