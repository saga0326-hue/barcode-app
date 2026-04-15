import streamlit as st
import pandas as pd
import requests
import json

st.set_page_config(page_title="專業商品條碼系統", layout="wide", page_icon="📦")

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
SCRIPT_URL = st.secrets.get("script_url", "") # 新增寫入網址

st.title("🛡️ 團隊共享：條碼系統")

df_main = fetch_data(DATA_URL)
df_cat = fetch_data(CAT_URL)

# --- 側邊欄：新增功能 ---
st.sidebar.header("➕ 新增商品 (至 Categories)")
with st.sidebar.expander("點此填寫新商品資訊"):
    new_type = st.text_input("類型 (例如: 扭蛋)")
    new_name = st.text_input("品名")
    new_bc = st.text_input("條碼")
    
    if st.button("確認送出"):
        if new_type and new_name and new_bc:
            if SCRIPT_URL:
                payload = {
                    "type": new_type,
                    "name": new_name,
                    "barcode": new_bc
                }
                try:
                    # 發送 POST 請求到 Google Apps Script
                    response = requests.post(SCRIPT_URL, data=json.dumps(payload))
                    if response.text == "Success":
                        st.sidebar.success("✅ 已成功新增至雲端！")
                        st.cache_data.clear() # 清除快取以便看到新資料
                    else:
                        st.sidebar.error("❌ 新增失敗，請檢查 Script 設定")
                except Exception as e:
                    st.sidebar.error(f"連線錯誤: {e}")
            else:
                st.sidebar.warning("請先在 Secrets 設定 script_url")
        else:
            st.sidebar.warning("請填寫完整三個欄位")

st.sidebar.markdown("---")

# --- 原有的篩選與顯示邏輯 ---
st.sidebar.header("🔍 篩選與設定")
img_size = st.sidebar.slider("圖片/條碼大小", 50, 300, 150, 10)
sort_order = st.sidebar.radio("排序方式", ["品名遞增 (A-Z)", "品名遞減 (Z-A)"])

# 分類選單
selected_type = "全部"
if isinstance(df_cat, pd.DataFrame) and '類型' in df_cat.columns:
    unique_types = df_cat['類型'].dropna().unique().tolist()
    cat_list = ["全部"] + sorted([str(t) for t in unique_types if t])
    selected_type = st.sidebar.selectbox("📂 常用類型快選", cat_list)

search_name = st.sidebar.text_input("品名搜尋")
search_code = st.sidebar.text_input("條碼/代號搜尋")

# (以下顯示邏輯與你之前的正確版一致...)
if isinstance(df_main, pd.DataFrame) and isinstance(df_cat, pd.DataFrame):
    if selected_type == "全部":
        work_df = df_main.copy()
        source_label = "主資料庫 (Data)"
    else:
        work_df = df_cat[df_cat['類型'] == selected_type].copy()
        source_label = f"分類表 (Categories) - {selected_type}"

    if search_name:
        work_df = work_df[work_df['品名'].str.contains(search_name, na=False)]
    if search_code:
        mask = pd.Series([False] * len(work_df), index=work_df.index)
        if '條碼' in work_df.columns:
            mask |= work_df['條碼'].str.contains(search_code, na=False)
        if '商品代號' in work_df.columns:
            mask |= work_df['商品代號'].str.contains(search_code, na=False)
        work_df = work_df[mask]

    if not work_df.empty and '品名' in work_df.columns:
        is_ascending = True if sort_order == "品名遞增 (A-Z)" else False
        work_df = work_df.sort_values(by='品名', ascending=is_ascending)

    if search_name or search_code or selected_type != "全部":
        st.caption(f"📍 目前搜尋範圍：{source_label}")
        st.success(f"找到 {len(work_df)} 筆結果")
        for _, row in work_df.head(100).iterrows():
            bc_val = str(row.get('條碼', '')).replace('*', '').strip()
            item_id = str(row.get('商品代號', ''))
            img_url = str(row.get('圖片', '')).strip()
            display_name = row.get('品名', '未知品名')
            
            sub_title = ""
            if selected_type != "全部" and bc_val and bc_val != 'nan' and bc_val != '':
                data_match = df_main[df_main['條碼'] == bc_val]
                if not data_match.empty:
                    data_name = data_match.iloc[0].get('品名', '')
                    if data_name != display_name:
                        sub_title = f"原始品名：{data_name}"

            has_image = isinstance(img_url, str) and img_url.startswith('http')
            with st.container():
                if has_image:
                    col_bc, col_info, col_img = st.columns([1.5, 3, 1.5])
                else:
                    col_bc, col_info = st.columns([1.5, 4.5])
                with col_bc:
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
        st.info("💡 請在左側輸入搜尋條件。")
        st.metric("雲端總品項 (Data)", len(df_main))
else:
    st.error("資料庫連線中...")
