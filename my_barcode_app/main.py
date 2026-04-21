import streamlit as st
import pandas as pd
import requests
import json

# 1. 基本頁面設定
st.set_page_config(page_title="專業商品條碼系統", layout="wide", page_icon="📦")

# 2. 強化版讀取函式 (修正 AttributeError)
@st.cache_data(ttl=60)
def fetch_data(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        # 先以字串讀取
        df = pd.read_csv(url, dtype=str, storage_options=headers)
        df.columns = df.columns.str.strip()
        
        # 修正點：先將 NaN 轉為空字串，再執行 strip 與 replace
        for col in df.columns:
            df[col] = df[col].fillna("").astype(str).str.strip()
            if col == '條碼':
                df[col] = df[col].str.replace('*', '', regex=False)
        return df
    except Exception as e:
        return f"ERROR: {str(e)}"

# 3. 取得網址 (從 Secrets 讀取)
try:
    DATA_URL = st.secrets["data_url"]
    CAT_URL = st.secrets["cat_url"]
    SCRIPT_URL = st.secrets.get("script_url", "")
except:
    st.error("❌ 請檢查 .streamlit/secrets.toml 設定")
    st.stop()

st.title("🛡️ 團隊共享：條碼系統")

df_main = fetch_data(DATA_URL)
df_cat = fetch_data(CAT_URL)

# 檢查資料是否成功讀取
if isinstance(df_main, str) or isinstance(df_cat, str):
    st.error(f"資料載入失敗: {df_main if isinstance(df_main, str) else df_cat}")
    st.stop()

# --- 側邊欄控制區 ---
st.sidebar.header("🔍 篩選與設定")
img_size = st.sidebar.slider("圖片/條碼顯示大小", 50, 300, 150, 10)
sort_order = st.sidebar.radio("排序方式", ["品名遞增 (A-Z)", "品名遞減 (Z-A)"])

unique_types = sorted([str(t) for t in df_cat['類型'].unique() if t and t != 'nan'])
selected_type = st.sidebar.selectbox("📂 常用類型快選", ["全部"] + unique_types)

search_name = st.sidebar.text_input("📝 品名搜尋")

# 條碼搜尋 (數字輸入優化)
search_code_num = st.sidebar.number_input("🔢 條碼/代號搜尋", value=0, step=1, format="%d")
search_code = str(search_code_num) if search_code_num != 0 else ""

st.sidebar.markdown("---")

# --- 側邊欄：新增商品區 ---
st.sidebar.header("➕ 新增商品")
with st.sidebar.expander("展開填寫新資訊"):
    type_options = unique_types + ["➕ 新增其他類別..."]
    chosen_type = st.selectbox("選擇類別", type_options)
    final_type = st.text_input("新類別名稱") if chosen_type == "➕ 新增其他類別..." else chosen_type
    
    new_name = st.text_input("商品品名 (必填)")
    new_bc_num = st.number_input("商品條碼 (必填)", value=0, step=1, format="%d")
    new_bc = str(new_bc_num) if new_bc_num != 0 else ""
    
    if st.button("🚀 確認送出"):
        if final_type and new_name and new_bc:
            payload = {"type": final_type, "name": new_name, "barcode": new_bc}
            try:
                res = requests.post(SCRIPT_URL, data=json.dumps(payload))
                if "Success" in res.text:
                    st.sidebar.success("✅ 新增成功！")
                    st.cache_data.clear()
                else: st.sidebar.error("❌ 寫入失敗")
            except: st.sidebar.error("❌ 連線錯誤")
        else: st.sidebar.warning("請填寫完整資訊")

# --- 核心邏輯：顯示搜尋結果 ---
work_df = df_main.copy() if selected_type == "全部" else df_cat[df_cat['類型'] == selected_type].copy()

if search_name:
    work_df = work_df[work_df['品名'].str.contains(search_name, na=False)]
if search_code:
    mask = work_df['條碼'].str.contains(search_code, na=False)
    if '商品代號' in work_df.columns:
        mask |= work_df['商品代號'].str.contains(search_code, na=False)
    work_df = work_df[mask]

# 排序與限制顯示數量
is_ascending = (sort_order == "品名遞增 (A-Z)")
work_df = work_df.sort_values(by='品名', ascending=is_ascending).head(50)

if not work_df.empty:
    st.success(f"找到 {len(work_df)} 筆結果")
    for _, row in work_df.iterrows():
        bc_val = row.get('條碼', '')
        has_image = '圖片' in row and row['圖片'].startswith('http')
        
        with st.container():
            cols = st.columns([1.5, 3, 1.5]) if has_image else st.columns([1.5, 4.5])
            with cols[0]:
                if bc_val:
                    st.image(f"https://bwipjs-api.metafloor.com/?bcid=code128&text={bc_val}&scale=2&includetext", width=img_size)
                else: st.caption("無條碼")
            with cols[1]:
                st.markdown(f"### {row['品名']}")
                st.write(f"**口座:** `{row.get('口座', '-')}` | **代號:** `{row.get('商品代號', '-')}`")
            if has_image:
                with cols[2]: st.image(row['圖片'], width=img_size)
        st.divider()
else:
    st.info("💡 查無資料，請嘗試調整搜尋條件。")
