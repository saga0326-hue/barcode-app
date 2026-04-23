import streamlit as st
import pandas as pd
import requests
import json
import streamlit.components.v1 as components

# 1. 頁面基礎設定
st.set_page_config(
    page_title="專業商品條碼系統", 
    layout="wide", 
    page_icon="📦",
    initial_sidebar_state="collapsed" 
)

# --- 核心：精準控制鍵盤類型 ---
def force_smart_keyboard():
    components.html(
        """
        <script>
            var inputs = window.parent.document.querySelectorAll("input[type='text']");
            for (var i = 0; i < inputs.length; i++) {
                var placeholder = inputs[i].getAttribute("placeholder") || "";
                if (placeholder.includes("數字") || placeholder.includes("條碼")) {
                    inputs[i].setAttribute("inputmode", "numeric");
                    inputs[i].setAttribute("pattern", "[0-9]*");
                } else {
                    inputs[i].setAttribute("inputmode", "text");
                }
            }
        </script>
        """,
        height=0,
    )

# 2. 數據讀取與快取邏輯
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

# 3. 讀取 Secrets 設定
try:
    DATA_URL = st.secrets["data_url"]
    CAT_URL = st.secrets["cat_url"]
    SCRIPT_URL = st.secrets.get("script_url", "")
except:
    st.error("❌ 請檢查 .streamlit/secrets.toml 設定")
    st.stop()

# --- 主程式開始 ---
st.markdown("### 🛡️ 團隊共享條碼系統")
force_smart_keyboard()

df_main = fetch_data(DATA_URL)
df_cat = fetch_data(CAT_URL)

if isinstance(df_main, pd.DataFrame):
    # 手機版分頁設計
    tab_search, tab_add, tab_settings = st.tabs(["🔍 快速搜尋", "➕ 新增品項", "⚙️ 設定"])

    # --- Tab 3: 系統設定 (優先定義以獲取排序與大小參數) ---
    with tab_settings:
        st.markdown("#### 🖼️ 顯示設定")
        img_size = st.slider("調整條碼/圖片大小", 50, 400, 150, 10)
        
        st.divider()
        st.markdown("#### 🔃 排序設定")
        # 將排序功能移至此處
        sort_choice = st.radio("搜尋結果排序方式 (依品名)", ["遞增 (A-Z)", "遞減 (Z-A)"], index=1)
        is_ascending = True if sort_choice == "遞增 (A-Z)" else False
        
        st.divider()
        st.markdown("#### 🔄 數據維護")
        if st.button("強制重新整理資料庫", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    # --- Tab 1: 搜尋與顯示 ---
    with tab_search:
        unique_types = sorted([str(t) for t in df_cat['類型'].unique() if t and t != 'nan'])
        selected_type = st.selectbox("📂 選擇類別", ["全部"] + unique_types)

        search_name = st.text_input("📝 品名關鍵字", placeholder="輸入品名搜尋...")
        search_code = st.text_input("🔢 條碼/代號搜尋", placeholder="點擊輸入數字條碼...")

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

            # 根據「設定」分頁的 sort_choice 進行排序
            work_df = work_df.sort_values(by='品名', ascending=is_ascending).head(50)

            if not work_df.empty:
                st.caption(f"找到 {len(work_df)} 筆結果 (排序：{sort_choice})")
                for _, row in work_df.iterrows():
                    bc_val = row.get('條碼', '')
                    has_image = '圖片' in row and str(row['圖片']).startswith('http')
                    
                    with st.container(border=True):
                        c1, c2 = st.columns([1.5, 3])
                        with c1:
                            if bc_val:
                                st.image(f"https://bwipjs-api.metafloor.com/?bcid=code128&text={bc_val}&scale=2&includetext", width=img_size)
                            else:
                                st.caption("無條碼資訊")
                        with c2:
                            st.markdown(f"**{row['品名']}**")
                            st.caption(f"口座: `{row.get('口座', '-')}` | 代號: `{row.get('商品代號', '-')}`")
                            if has_image:
                                with st.expander("📸 查看商品圖"):
                                    st.image(row['圖片'], width=img_size)
            else:
                st.warning("查無符合資料")
        else:
            st.info("👋 請輸入搜尋關鍵字或選擇類別")
            st.metric("資料庫總品項", len(df_main))

    # --- Tab 2: 新增商品 ---
    with tab_add:
        st.markdown("#### ➕ 新增商品資訊")
        type_options = unique_types + ["➕ 新增其他類別..."]
        chosen_type = st.selectbox("選擇類別", type_options, key="add_type")
        final_type = st.text_input("新類別名稱") if chosen_type == "➕ 新增其他類別..." else chosen_type
        
        new_name = st.text_input("商品品名 (必填)", placeholder="請輸入完整名稱")
        new_bc = st.text_input("商品條碼 (必填)", placeholder="輸入條碼數字")
        
        if st.button("🚀 確認送出並寫入", use_container_width=True):
            if final_type and new_name and new_bc:
                payload = {"type": final_type, "name": new_name, "barcode": new_bc}
                try:
                    res = requests.post(SCRIPT_URL, data=json.dumps(payload))
                    if "Success" in res.text:
                        st.success("✅ 寫入成功！")
                        st.cache_data.clear()
                    else: st.error(f"❌ 失敗: {res.text}")
                except: st.error("❌ 無法連線至自動化腳本")
            else: st.warning("請填寫所有必要欄位")
else:
    st.error("⚠️ 資料源連線失敗")
