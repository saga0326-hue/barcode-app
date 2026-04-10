import streamlit as st
import pandas as pd

# 1. 頁面基本設定
st.set_page_config(page_title="專業商品條碼檢索系統", layout="wide", page_icon="📦")

# 2. 定義資料讀取函式 (加入 dtype=str 解決 07 口座變 7 的問題)
@st.cache_data
def load_data(file):
    # 將所有欄位強制讀取為字串，確保前導零、長條碼數字不被轉換
    return pd.read_excel(file, dtype=str)

st.title("🛡️ 商品稽核與條碼分享系統")
st.markdown("---")

# 3. 檔案上傳區
uploaded_file = st.file_uploader("請上傳您的商品 Excel 檔案", type=["xlsx"])

if uploaded_file:
    # 讀取資料
    df = load_data(uploaded_file)
    
    # 4. 側邊欄：獨立搜尋控制區
    st.sidebar.header("🔍 篩選條件")
    st.sidebar.info("在下方輸入關鍵字進行精確檢索")
    
    search_name = st.sidebar.text_input("品名搜尋", placeholder="例如：外套")
    search_loc = st.sidebar.text_input("口座搜尋", placeholder="例如：07")
    search_code = st.sidebar.text_input("代號/條碼搜尋", placeholder="輸入完整或部分數字")

    # 5. 判斷是否有搜尋行為
    has_search = search_name or search_loc or search_code

    if has_search:
        # 執行篩選邏輯 (na=False 防止空白格出錯)
        filtered_df = df.copy()
        
        if search_name:
            filtered_df = filtered_df[filtered_df['品名'].str.contains(search_name, na=False)]
        
        if search_loc:
            # 因為已經轉成字串，這裡搜尋 "07" 就能精準匹配
            filtered_df = filtered_df[filtered_df['口座'].str.contains(search_loc, na=False)]
            
        if search_code:
            # 同時比對「條碼」與「商品代號」
            mask = (filtered_df['條碼'].str.contains(search_code, na=False) | 
                    filtered_df['商品代號'].str.contains(search_code, na=False))
            filtered_df = filtered_df[mask]

        # 6. 顯示搜尋結果
        count = len(filtered_df)
        st.subheader(f"📊 檢索結果 (共 {count} 筆)")

        if count == 0:
            st.warning("查無符合資料，請確認輸入內容。")
        elif count > 50:
            st.warning("結果過多（超過 50 筆），僅顯示前 50 筆，請增加搜尋條件縮小範圍。")
            display_df = filtered_df.head(50)
        else:
            display_df = filtered_df

        # 7. 產出商品卡片與條碼
        for _, row in display_df.iterrows():
            # 自動清理條碼中的 * 號
            raw_barcode = str(row['條碼'])
            clean_barcode = raw_barcode.strip('*')
            
            with st.container():
                # 建立左右兩欄：左邊文字資訊，右邊條碼圖片
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.markdown(f"### {row['品名']}")
                    # 使用小標籤樣式顯示資訊
                    st.markdown(f"**📍 口座位置：** `{row['口座']}`")
                    st.markdown(f"**🆔 商品代號：** `{row['商品代號']}`")
                    st.markdown(f"**🔢 原始條碼：** `{raw_barcode}`")
                
                with col2:
                    # 使用 bwip-js API 生成條碼圖片 (Code 128)
                    barcode_url = f"https://bwipjs-api.metafloor.com/?bcid=code128&text={clean_barcode}&scale=3&rotate=N&includetext"
                    st.image(barcode_url, caption="掃描槍專用條碼", use_container_width=True)
                
                st.markdown("---") # 每一筆之間的分割線
    else:
        # 初始畫面提示
        st.info("💡 請利用左側搜尋框輸入條件。您可以單獨搜尋，也可以組合搜尋（例如：特定口座中的特定品名）。")
        
        # 顯示簡易的數據統計
        st.write(f"當前載入資料庫：**{len(df)}** 筆商品")

else:
    # 尚未上傳檔案時的導引
    st.write("### 歡迎使用！")
    st.write("請先將包含以下標題列的 Excel 檔案上傳：")
    st.code("品名 | 條碼 | 商品代號 | 口座", language="text")