import streamlit as st
import pandas as pd
import requests
import json
import streamlit.components.v1 as components

# 1. 基本頁面設定
st.set_page_config(page_title="專業商品條碼系統", layout="wide", page_icon="📦")

# --- 核心：強制手機跳出數字鍵盤的 JavaScript ---
# 這段程式碼會尋找所有的 input 框，並將其類型改為 tel (最適合輸入條碼的數字鍵盤)
def force_numeric_keyboard():
    components.html(
        """
        <script>
            var input = window.parent.document.querySelectorAll("input[type='text']");
            for (var i = 0; i < input.length; i++) {
                input[i].setAttribute("inputmode", "numeric");
                input[i].setAttribute("pattern", "[0-9]*");
            }
        </script>
        """,
        height=0,
    )

# 2. 強化版讀取函式
@st.cache_data(ttl=60)
def fetch_data(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        df = pd.read_csv(url, dtype=str, storage_options=headers)
        df.columns = df.columns.str.strip()
        for col in df.columns:
            df[col] = df[col].fillna("").astype(str).str.strip()
            if col == '條碼':
                df[col] = df[col].str.replace('*', '', regex=False)
        return df
    except Exception as e:
        return f"ERROR: {str(e)}"

# 3. 取得網址
try:
    DATA_URL = st.secrets["data_url"]
    CAT_URL = st.secrets["cat_url"]
    SCRIPT_URL = st.secrets.get("script_url", "")
except:
    st.error("❌ 請檢查 .streamlit/secrets.toml 設定")
    st.stop()

st.title("🛡️ 團隊共享：條碼系統")
force_numeric_keyboard() # 執行 JS 腳本

df_main = fetch_data(DATA_URL)
df_cat = fetch_data(CAT_URL)

# --- 側邊欄控制區 ---
st.sidebar.header("🔍 篩選與設定")
img_size = st.sidebar.slider("圖片/條碼大小", 50, 300, 150, 10)
sort_order = st.sidebar.radio("排序方式", ["品名遞增 (A-Z)", "品名遞減 (Z-A)"])

unique_types = sorted([str(t) for t in df_cat['類型'].unique() if t and t != 'nan'])
selected_type = st.sidebar.selectbox("📂 常用類型快選", ["全部"] + unique_types)

search_name = st.sidebar.text_input("📝 品名搜尋", placeholder="輸入名稱...")

# 使用 text_input 確保沒有加減號，JS 會負責讓它跳出數字鍵盤
search_code = st.sidebar.text_input("🔢 條碼/代號搜尋", placeholder="點擊此處輸入數字...")

st.sidebar.markdown("---")

# --- 側邊欄：新增商品區 ---
st.sidebar.header("➕ 新增商品")
with st.sidebar.expander("展開填寫新資訊"):
    type_options = unique_types + ["➕ 新增其他類別..."]
    chosen_type = st.selectbox("選擇類別", type_options)
    final_type = st.text_input("新類別名稱") if chosen_type == "➕ 新增其他類別..." else chosen_type
    
    new_name = st.text_input("商品品名 (必填)")
    new_bc = st.text_input("商品條碼 (必填)", placeholder="直接輸入條碼...")
    
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
if isinstance(df_main, pd.DataFrame):
    # 邏輯優化：只有在非「全部」或有輸入文字時才顯示結果
    has_search = (search_name != "") or (search_code != "") or (selected_type != "全部")

    if has_search:
        work_df = df_main.copy() if selected_type == "全部" else df_cat[df_cat['類型'] == selected_type].copy()

        if search_name:
            work_df = work_df[work_df['品名'].str.contains(search_name, na=False, case=False)]
        if search_code:
            mask = work_df['條碼'].str.contains(search_code, na=False)
            if '商品代號' in work_df.columns:
                mask |= work_df['商品代號'].str.contains(search_code, na=False)
            work_df = work_df[mask]

        is_ascending = (sort_order == "品名遞增 (A-Z)")
        work_df = work_df.sort_values(by='品名', ascending=is_ascending).head(100)

        if not work_df.empty:
            st.success(f"找到 {len(work_df)} 筆結果")
            for _, row in work_df.iterrows():
                bc_val = row.get('條碼', '')
                has_image = '圖片' in row and str(row['圖片']).startswith('http')
                
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
            st.warning("查無符合條件的商品。")
    else:
        # 預設不顯示【全部】資料庫內容
        st.info("👋 請在左側輸入搜尋關鍵字，或選擇特定類別來查看商品。")
        st.divider()
        st.metric("資料庫總品項", len(df_main))
