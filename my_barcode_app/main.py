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

st.title("🛡️ 團隊共享：雲端商品管理系統")

df = fetch_data(DATA_URL)
df_cat = fetch_data(CAT_URL)

# --- 側邊欄 ---
st.sidebar.header("🔍 篩選與設定")
img_size = st.sidebar.slider("圖片/條碼大小", 50, 300, 150, 10)

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
    
    # 篩選邏輯
    if selected_type != "全部" and isinstance(df_cat, pd.DataFrame):
        target_barcodes = df_cat[df_cat['類型'] == selected_type]['條碼'].unique().tolist()
        filtered_df = filtered_df[filtered_df['條碼'].isin(target_barcodes)]
    
    if search_name:
        filtered_df = filtered_df[filtered_df['品名'].str.contains(search_name, na=False)]
    if search_code:
        mask = (filtered_df['條碼'].str.contains(search_code, na=False) | 
                filtered_df['商品代號'].str.contains(search_code, na=False))
        filtered_df = filtered_df[mask]

    if search_name or search_code or selected_type != "全部":
        st.success(f"找到 {len(filtered_df)} 筆結果")
        
        for _, row in filtered_df.head(100).iterrows():
            bc_val = str(row.get('條碼', '')).replace('*', '').strip()
            item_id = str(row.get('商品代號', ''))
            
            with st.container():
                col_bc, col_info, col_img = st.columns([1.5, 3, 1.5])
                with col_bc:
                    if bc_val and bc_val != 'nan':
                        # 重新加入條碼產生器
                        bc_api = f"https://bwipjs-api.metafloor.com/?bcid=code128&text={bc_val}&scale=2&rotate=N&includetext"
                        st.image(bc_api, width=img_size)
                with col_info:
                    st.markdown(f"### {row.get('品名', '未知品名')}")
                    st.write(f"**口味/口味代號:** {row.get('口座', '-')}")
                    st.write(f"**商品代號:** {item_id}")
                with col_img:
                    # 顯示圖片欄位的網址或預設圖
                    img_url = row.get('圖片', '')
                    if isinstance(img_url, str) and img_url.startswith('http'):
                        st.image(img_url, width=img_size)
                    else:
                        st.image("https://via.placeholder.com/150?text=No+Image", width=img_size)
            st.divider()
    else:
        st.metric("雲端總品項", len(df))
else:
    st.error("資料庫連線中...")
