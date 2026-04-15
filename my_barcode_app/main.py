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

df = fetch_data(DATA_URL)
df_cat = fetch_data(CAT_URL)

# --- 側邊欄 ---
st.sidebar.header("🔍 篩選與設定")
img_size = st.sidebar.slider("圖片/條碼大小", 50, 300, 150, 10)
sort_order = st.sidebar.radio("排序方式", ["品名遞增 (A-Z)", "品名遞減 (Z-A)"])

selected_type = "全部"
if isinstance(df_cat, pd.DataFrame) and '類型' in df_cat.columns:
    unique_types = df_cat['類型'].dropna().unique().tolist()
    cat_list = ["全部"] + sorted([str(t) for t in unique_types if t])
    selected_type = st.sidebar.selectbox("📂 常用類型快選", cat_list)

search_name = st.sidebar.text_input("品名搜尋")
search_code = st.sidebar.text_input("條碼/代號搜尋")

# --- 主畫面顯示 ---
if isinstance(df, pd.DataFrame):
    filtered_df = df.copy()
    
    # 1. 篩選邏輯
    if selected_type != "全部" and isinstance(df_cat, pd.DataFrame):
        target_barcodes = df_cat[df_cat['類型'] == selected_type]['條碼'].unique().tolist()
        filtered_df = filtered_df[filtered_df['條碼'].isin(target_barcodes)]
    
    if search_name:
        filtered_df = filtered_df[filtered_df['品名'].str.contains(search_name, na=False)]
    if search_code:
        mask = (filtered_df['條碼'].str.contains(search_code, na=False) | 
                filtered_df['商品代號'].str.contains(search_code, na=False))
        filtered_df = filtered_df[mask]

    # 2. 品名排序
    if not filtered_df.empty and '品名' in filtered_df.columns:
        is_ascending = True if sort_order == "品名遞增 (A-Z)" else False
        filtered_df = filtered_df.sort_values(by='品名', ascending=is_ascending)

    # 3. 顯示結果
    if search_name or search_code or selected_type != "全部":
        st.success(f"找到 {len(filtered_df)} 筆結果")
        
        for _, row in filtered_df.head(100).iterrows():
            bc_val = str(row.get('條碼', '')).replace('*', '').strip()
            item_id = str(row.get('商品代號', ''))
            img_url = str(row.get('圖片', '')).strip()
            
            # 取得 Data 的品名
            main_name = row.get('品名', '未知品名')
            
            # --- 雙品名比對機制 ---
            sub_name = ""
            if isinstance(df_cat, pd.DataFrame) and bc_val:
                # 在 Categories 表中根據條碼尋找對應的品名
                cat_match = df_cat[df_cat['條碼'] == bc_val]
                if not cat_match.empty:
                    sub_name = cat_match.iloc[0].get('品名', '')
            
            has_image = isinstance(img_url, str) and img_url.startswith('http')
            
            with st.container():
                if has_image:
                    col_bc, col_info, col_img = st.columns([1.5, 3, 1.5])
                else:
                    col_bc, col_info = st.columns([1.5, 4.5])
                
                with col_bc:
                    if bc_val and bc_val != 'nan':
                        bc_api = f"https://bwipjs-api.metafloor.com/?bcid=code128&text={bc_val}&scale=2&rotate=N&includetext"
                        st.image(bc_api, width=img_size)
                
                with col_info:
                    st.markdown(f"### {main_name}")
