import streamlit as st
import pandas as pd
import os

# 1. 基本頁面設定
st.set_page_config(page_title="專業商品條碼系統", layout="wide", page_icon="📦")

# 2. 強化版讀取函式
@st.cache_data(ttl=60)
def fetch_data(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        df = pd.read_csv(url, dtype=str, storage_options=headers)
        # 清除標題與內容的所有前後空白，避免抓不到欄位
        df.columns = df.columns.str.strip()
        df = df.apply(lambda x: x.str.strip() if isinstance(x, str) else x)
        return df
    except Exception as e:
        return f"ERROR: {str(e)}"

# 3. 取得網址 (從 Secrets 抓取)
DATA_URL = st.secrets["data_url"]
CAT_URL = st.secrets["cat_url"]

# 修改後的標題
st.title("🛡️ 團隊共享：條碼系統")

df_main = fetch_data(DATA_URL)
df_cat = fetch_data(CAT_URL)

# --- 側邊欄控制區 ---
st.sidebar.header("🔍 篩選與設定")
img_size = st.sidebar.slider("圖片/條碼大小", 50, 300, 150, 10)
sort_order = st.sidebar.radio("排序方式", ["品名遞增 (A-Z)", "品名遞減 (Z-A)"])

# 建立常用類型快選選單
selected_type = "全部"
if isinstance(df_cat, pd.DataFrame) and '類型' in df_cat.columns:
    unique_types = df_cat['類型'].dropna().unique().tolist()
    cat_list = ["全部"] + sorted([str(t) for t in unique_types if str(t) != 'nan' and str(t) != ''])
    selected_type = st.sidebar.selectbox("📂 常用類型快選", cat_list)

search_name = st.sidebar.text_input("品名搜尋")
search_code = st.sidebar.text_input("條碼/代號搜尋")

# --- 核心邏輯：動態切換資料庫 ---
if isinstance(df_main, pd.DataFrame) and isinstance(df_cat, pd.DataFrame):
    
    # 決定基礎資料來源
    if selected_type == "全部":
        # 模式 A: 使用完整的 Data 資料庫
        work_df = df_main.copy()
        source_label = "主資料庫 (Data)"
    else:
        # 模式 B: 切換至 Categories 資料庫並鎖定該類型
        work_df = df_cat[df_cat['類型'] == selected_type].copy()
        source_label = f"分類表 (Categories) - {selected_type}"

    # 執行關鍵字過濾
    if search_name:
        work_df = work_df[work_df['品名'].str.contains(search_name, na=False)]
        
    if search_code:
        mask = pd.Series([False] * len(work_df), index=work_df.index)
        if '條碼' in work_df.columns:
            mask |= work_df['條碼'].str.contains(search_code, na=False)
        if '商品代號' in work_df.columns:
            mask |= work_df['商品代號'].str.contains(search_code, na=False)
        # 確保括號已完整閉合
        work_df = work_df[mask]

    # 品名排序
    if not work_df.empty and '品名' in work_df.columns:
        is_ascending = True if sort_order == "品名遞增 (A-Z)" else False
        work_df = work_df.sort_values(by='品名', ascending=is_ascending)

    # 顯示搜尋結果
    if search_name or search_code or selected_type != "全部":
        st.caption(f"📍 目前搜尋範圍：{source_label}")
        st.success(f"找到 {len(work_df)} 筆結果")
        
        for _, row in work_df.head(100).iterrows():
            # 確保抓取條碼資訊
            bc_val = str(row.get('條碼', '')).replace('*', '').strip()
            item_id = str(row.get('商品代號', ''))
            img_url = str(row.get('圖片', '')).strip()
            display_name = row.get('品名', '未知品名')
            
            # 反向比對 Data 的原始品名作為小字提醒
            sub_title = ""
            if selected_type != "全部" and bc_val and bc_val != 'nan' and bc_val != '':
                data_match = df_main[df_main['條碼'] == bc_val]
                if not data_match.empty:
                    data_name = data_match.iloc[0].get('品名', '')
                    if data_name != display_name:
                        sub_title = f"原始品名：{data_name}"

            # 檢查有無有效的圖片網址
            has_image = isinstance(img_url, str) and img_url.startswith('http')
            
            with st.container():
                # 佈局配置：有圖三欄，沒圖兩欄
                if has_image:
                    col_bc, col_info, col_img = st.columns([1.5, 3, 1.5])
                else:
                    col_bc, col_info = st.columns([1.5, 4.5])
                
                with col_bc:
                    # 產出條碼圖片
                    if bc_val and bc_val != 'nan' and bc_val != '':
                        bc_api = f"https://bwipjs-api.metafloor.com/?bcid=code128&text={bc_val}&scale=2&rotate=N&includetext"
                        st.image(bc_api, width=img_size)
                    else:
                        st.caption("⚠️ 無條碼資料")
                
                with col_info:
                    st.markdown(f"### {display_name}")
                    if sub_title:
                        st.caption(sub_title)
                    st.write(f"**口座:** {row.get('口座', '-')}")
                    st.write(f"**商品代號:** {item_id}")
                
                if has_image:
                    with col_img:
                        st.image(img_url, width=img_size)
            st.divider()
    else:
        st.info("💡 請在左側輸入搜尋條件或選擇常用類型。")
        st.metric("雲端總品項 (Data)", len(df_main))
else:
    st.error("資料庫讀取中，請稍候。若持續未回應，請檢查 Google Sheets 發布設定與 Secrets 網址。")
