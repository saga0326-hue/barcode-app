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

# --- 核心：九宮格數字鍵盤腳本 ---
def force_numeric_pad():
    components.html(
        """
        <script>
            const fixInputs = () => {
                const inputs = window.parent.document.querySelectorAll("input[type='number']");
                inputs.forEach(input => {
                    input.setAttribute("inputmode", "numeric");
                    input.setAttribute("pattern", "[0-9]*");
                });
            };
            const observer = new MutationObserver(fixInputs);
            observer.observe(window.parent.document.body, { childList: true, subtree: true });
            fixInputs();
        </script>
        """,
        height=0,
    )

# 2. 數據讀取邏輯
@st.cache_data(ttl=30)
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

# 3. 讀取 Secrets
try:
    DATA_URL = st.secrets["data_url"]
    CAT_URL = st.secrets["cat_url"]
    SCRIPT_URL = st.secrets.get("script_url", "")
except:
    st.error("❌ 請檢查 Secrets 設定")
    st.stop()

# --- 主程式 ---
force_numeric_pad()
st.markdown("### 🛡️ 團隊共享條碼系統")

df_main = fetch_data(DATA_URL)
df_cat = fetch_data(CAT_URL)

if isinstance(df_main, pd.DataFrame):
    tab_search, tab_add, tab_settings, tab_feedback = st.tabs(["🔍 快速搜尋", "➕ 新增品項", "⚙️ 設定", "💬 意見反映"])

    # --- Tab 3: 設定 (提供預設值) ---
    with tab_settings:
        st.markdown("#### 🔃 預設排序設定")
        sort_choice = st.radio("排序方式", ["遞增 (A-Z)", "遞減 (Z-A)"], index=0)
        is_ascending = True if sort_choice == "遞增 (A-Z)" else False
        if st.button("🔄 強制刷新資料庫", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    # --- Tab 1: 快速搜尋 ---
    with tab_search:
        # 第一行並排：類別與口座
        c1, c2 = st.columns(2)
        with c1:
            unique_types = sorted([str(t) for t in df_cat['類型'].unique() if t and t != 'nan'])
            selected_type = st.selectbox("📂 類別", ["全部"] + unique_types)
        with c2:
            # 關鍵修改：篩選特定的口座 (04, 05, 07)
            # 先確認資料中是否存在這些口座
            target_koz = ["04", "05", "07"]
            # 從 data 提取現有的口座進行比對 (或是直接顯示這三個)
            selected_koz = st.selectbox("🏦 口座", ["全部"] + target_koz)

        # 第二行並排：搜尋文字與排序(搬到這裡更方便)
        c3, c4 = st.columns([2, 1])
        with c3:
            search_name = st.text_input("📝 品名關鍵字", placeholder="輸入名稱...")
        with c4:
            # 讓使用者在搜尋頁就能改排序，不用跑去設定頁
            search_sort = st.selectbox("🔃 排序", ["A-Z", "Z-A"], index=0 if is_ascending else 1)
            final_asc = True if search_sort == "A-Z" else False

        # 條碼搜尋 (九宮格)
        search_code_num = st.number_input("🔢 條碼搜尋", step=1, value=None, key="main_search_bc")
        search_code = str(search_code_num) if search_code_num is not None else ""

        # --- 綜合篩選邏輯 ---
        has_search = (search_name != "") or (search_code != "") or (selected_type != "全部") or (selected_koz != "全部")

        if has_search:
            # 基礎資料源選擇
            work_df = df_main.copy() if selected_type == "全部" else df_cat[df_cat['類型'] == selected_type].copy()
            
            # 1. 口座篩選
            if selected_koz != "全部":
                work_df = work_df[work_df['口座'] == selected_koz]
            
            # 2. 品名篩選
            if search_name:
                work_df = work_df[work_df['品名'].str.contains(search_name, na=False, case=False)]
            
            # 3. 條碼篩選
            if search_code:
                work_df = work_df[work_df['條碼'].str.contains(search_code, na=False)]
            
            # 4. 排序與限制顯示數量
            work_df = work_df.sort_values(by='品名', ascending=final_asc).head(50)

            if not work_df.empty:
                st.caption(f"找到 {len(work_df)} 筆結果")
                for _, row in work_df.iterrows():
                    bc_val = row.get('條碼', '')
                    with st.container(border=True):
                        col_img, col_txt = st.columns([1.5, 3])
                        with col_img:
                            if bc_val:
                                st.image(f"https://bwipjs-api.metafloor.com/?bcid=code128&text={bc_val}&scale=2&includetext")
                            else: st.caption("無條碼")
                        with col_txt:
                            st.markdown(f"**{row['品名']}**")
                            st.caption(f"口座: `{row.get('口座', '-')}` | 代號: `{row.get('商品代號', '-')}`")
            else:
                st.warning("查無符合資料")
        else:
            st.info("👋 請輸入搜尋關鍵字或選擇篩選條件")

    # --- Tab 2 & Tab 4 (維持原樣) ---
    with tab_add:
        st.markdown("#### ➕ 新增商品資訊")
        new_name = st.text_input("商品品名")
        new_bc_num = st.number_input("商品條碼", step=1, value=None, key="add_new_bc")
        if st.button("🚀 確認送出", use_container_width=True):
            if new_name and new_bc_num:
                payload = {"method": "add_barcode", "type": "預設", "name": new_name, "barcode": str(new_bc_num)}
                requests.post(SCRIPT_URL, data=json.dumps(payload))
                st.success("成功！")
                st.cache_data.clear()

    with tab_feedback:
        st.markdown("#### 💬 意見反映")
        fb_content = st.text_area("反映內容")
        if st.button("🚀 提交", use_container_width=True):
            if fb_content:
                fb_payload = {"method": "feedback", "type": "意見", "user": "匿名", "content": fb_content}
                requests.post(SCRIPT_URL, data=json.dumps(fb_payload))
                st.success("已收到意見")
                st.balloons()
