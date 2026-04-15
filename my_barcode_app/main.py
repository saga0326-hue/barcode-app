import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="專業商品雲端管理系統", layout="wide", page_icon="📦")

@st.cache_data(ttl=60)
def fetch_data(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        df = pd.read_csv(url, dtype=str, storage_options=headers)
        df.columns = df.columns.str.strip()
        df = df.apply(lambda x: x.str.strip() if isinstance(x, str) else x)
        return df
    except Exception as e:
        return f"ERROR: {str(e)}"

# 取得網址
DATA_URL = st.secrets["data_url"]
CAT_URL = st.secrets["cat_url"]

st.title("🛡️ 團隊共享：條碼系統")

df_main = fetch_data(DATA_URL)
df_cat = fetch_data(CAT_URL)

# --- 側邊欄 ---
st.sidebar.header("🔍 篩選與設定")
img_size = st.sidebar.slider("圖片/條碼大小", 50, 300, 150, 10)
sort_order = st.sidebar.radio("排序方式", ["品名遞增 (A-Z)", "品名遞減 (Z-A)"])

# 建立分類選單
selected_type = "全部"
if isinstance(df_cat, pd.DataFrame) and '類型' in df_cat.columns:
    unique_types = df_cat['類型'].dropna().unique().tolist()
    cat_list = ["全部"] + sorted([str(t) for t in unique_types if t])
    selected_type = st.sidebar.selectbox("📂 常用類型快選", cat_list)

search_name = st.sidebar.text_input("品名搜尋")
search_code = st.sidebar.text_input("條碼/代號搜尋")

# --- 核心邏輯：根據選擇切換資料來源 ---
if isinstance(df_main, pd.DataFrame) and isinstance(df_cat, pd.DataFrame):
    
    # 決定基礎資料來源
    if selected_type == "全部":
        # 模式 A: 使用完整的 Data 資料庫
        work_df = df_main.copy()
        source_label = "主資料庫 (Data)"
    else:
        # 模式 B: 切換至 Categories 資料庫並過濾類型
        work_df = df_cat[df_cat['類型'] == selected_type].copy()
        source_label = f"分類表 (Categories) - {selected_type}"

    # 執行關鍵字過濾
    if search_name:
        work_df = work_df[work_df['品名'].str.contains(search_name, na=False)]
    if search_code:
        mask = (work_df['條碼'].str.contains(search_code, na=False) | 
                work_df['商品代號'].str.contains(search_code, na=False))
        work_df = work_df[mask]

    # 品名排序
    if not work_df.empty and '品名' in work_df.columns:
        is_ascending = True if sort_order == "品名遞增 (A-Z)" else False
        work_df = work_df.sort_values(by='品名', ascending=is_ascending)

    # 顯示結果
    if search_name or search_code or selected_type != "全部":
        st.caption(f"📍 目前搜尋範圍：{source_label}")
        st.success(f"找到 {len(work_df)} 筆結果")
        
        for _, row in work_df.head(100).iterrows():
            bc_val = str(row.get('條碼', '')).replace('*', '').strip()
            item_id = str(row.get('商品代號', ''))
            img_url = str(row.get('圖片', '')).strip()
            
            # 取得主要顯示名稱
            display_name = row.get('品名', '未知品名')
            
            # --- 雙品名比對 (若在分類模式，嘗試找 Data 的原始品名作對照) ---
            sub_title = ""
            if selected_type != "全部" and bc_val:
                data_match = df_main[df_main['條碼'] == bc_val]
                if not data_match.empty:
                    data_name = data_match.iloc[0].get('品名', '')
                    if data_name != display_name:
                        sub_
