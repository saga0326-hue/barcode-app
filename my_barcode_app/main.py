import streamlit as st
import pandas as pd
import requests
import json
import streamlit.components.v1 as components

# 1. 頁面基礎設定
st.set_page_config(page_title="專業商品條碼系統", layout="wide", page_icon="📦", initial_sidebar_state="collapsed")

# --- 更新日誌 ---
VERSION_HISTORY = """
**v1.5 (2024/04/24)**
- 🛠️ 修正：根據 categories 欄位順序 (類型, 品名, 條碼, 代號) 重新對齊。
- 🔄 變更：新增商品的「類別」回歸下拉選單。
- 🏦 保持：查詢頁面維持「迷你按鈕」以利 iPhone 快速操作。

v1.3 (2024/04/24)
- 🔄 修正：將新增商品的類別改回「下拉式選單」，避免誤觸。
- 🛠️ 修正：調整資料寫入邏輯，解決類別變成時間的問題。
- ⚙️ 新增：設定頁面下方增加版本更新日誌。

v1.2 (2024/04/24)

➕ 新增：設定頁面「版本資訊」區塊。
💄 優化：類別與口座篩選改用「迷你按鈕 (Segmented Control)」。
🛠️ 修正：修正意見反映提交時的變數錯誤 (NameError)。
🧹 移除：移除新增商品時的「選擇口座」選項。
v1.1 (2024/04/20)

➕ 新增：口座 (04, 05, 07) 快速篩選功能。
🔍 優化：自動喚起手機數字鍵盤 (九宮格模式)。
"""

# 2. 核心腳本
def force_numeric_pad():
    components.html("""<script>
        const fixInputs = () => {
            const inputs = window.parent.document.querySelectorAll("input[type='number']");
            inputs.forEach(input => { input.setAttribute("inputmode", "numeric"); input.setAttribute("pattern", "[0-9]*"); });
        };
        const observer = new MutationObserver(fixInputs);
        observer.observe(window.parent.document.body, { childList: true, subtree: true });
        fixInputs();
    </script>""", height=0)

@st.cache_data(ttl=30)
def fetch_data(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        df = pd.read_csv(url, dtype=str, storage_options=headers)
        df.columns = df.columns.str.strip()
        for col in df.columns:
            df[col] = df[col].fillna("").astype(str).str.strip()
            if col == '條碼': df[col] = df[col].str.replace('*', '', regex=False)
        return df
    except Exception as e: return f"ERROR: {str(e)}"

# 3. 讀取配置
try:
    DATA_URL = st.secrets["data_url"]
    CAT_URL = st.secrets["cat_url"]
    SCRIPT_URL = st.secrets.get("script_url", "")
except:
    st.error("❌ Secrets 配置錯誤")
    st.stop()

force_numeric_pad()
st.markdown("### 🛡️ 團隊共享條碼系統")

df_main = fetch_data(DATA_URL)
df_cat = fetch_data(CAT_URL)

if isinstance(df_main, pd.DataFrame):
    tab_search, tab_add, tab_settings, tab_feedback = st.tabs(["🔍搜尋", "➕新增", "⚙️設定", "💬反映"])

    # --- Tab 1: 搜尋 (iPhone 優化並排) ---
    with tab_search:
        unique_types = sorted([str(t) for t in df_cat['類型'].unique() if t and t != 'nan'])
        st.write("📂 **類別篩選**")
        selected_type = st.segmented_control("tsel", options=["全部"] + unique_types, default="全部", label_visibility="collapsed")
        st.write("🏦 **口座篩選**")
        selected_koz = st.segmented_control("ksel", options=["全部", "04", "05", "07"], default="全部", label_visibility="collapsed")
        
        st.divider()
        s_name = st.text_input("📝 品名關鍵字", placeholder="關鍵字...")
        s_code_n = st.number_input("🔢 條碼搜尋", step=1, value=None, key="sc")
        s_code = str(s_code_n) if s_code_n is not None else ""

        is_asc = st.session_state.get('is_ascending', True)
        if any([s_name, s_code, selected_type != "全部", selected_koz != "全部"]):
            w_df = df_main.copy() if selected_type == "全部" else df_cat[df_cat['類型'] == selected_type].copy()
            if selected_koz != "全部": w_df = w_df[w_df['口座'] == selected_koz]
            if s_name: w_df = w_df[w_df['品名'].str.contains(s_name, na=False, case=False)]
            if s_code: w_df = w_df[w_df['條碼'].str.contains(s_code, na=False)]
            w_df = w_df.sort_values(by='品名', ascending=is_asc).head(50)

            for _, r in w_df.iterrows():
                with st.container(border=True):
                    c1, c2 = st.columns([1.5, 3])
                    with c1: st.image(f"https://bwipjs-api.metafloor.com/?bcid=code128&text={r.get('條碼','')}&scale=2&includetext")
                    with c2:
                        st.markdown(f"**{r['品名']}**")
                        st.caption(f"口座: {r.get('口座','-')} | 代號: {r.get('商品代號','-')}")

    # --- Tab 2: 新增 (類別改回下拉選單) ---
    with tab_add:
        st.markdown("#### ➕ 新增商品")
        # 類別下拉選單
        u_types = sorted([str(t) for t in df_cat['類型'].unique() if t and t != 'nan'])
        chosen_type = st.selectbox("📂 選擇所屬類別", u_types + ["➕ 新增類別..."], index=0)
        final_type = st.text_input("📝 請輸入新類別名稱") if chosen_type == "➕ 新增類別..." else chosen_type
        
        new_name = st.text_input("📦 商品品名 (必填)")
        new_bc = st.number_input("🔢 商品條碼 (必填)", step=1, value=None, key="abc")
        
        if st.button("🚀 確認送出", use_container_width=True):
            if final_type and new_name and new_bc:
                # 配合 categories 欄位：類型, 品名, 條碼
                payload = {"method": "add_barcode", "type": final_type, "name": new_name, "barcode": str(new_bc)}
                res = requests.post(SCRIPT_URL, data=json.dumps(payload))
                if "Success" in res.text:
                    st.success(f"✅ 已成功寫入類別：{final_type}")
                    st.cache_data.clear()
                else: st.error(f"錯誤: {res.text}")
            else: st.warning("⚠️ 請填寫完整資訊")

    # --- Tab 3: 設定 ---
    with tab_settings:
        sort_choice = st.radio("品名排序方向", ["遞增 (A-Z)", "遞減 (Z-A)"], index=0)
        st.session_state['is_ascending'] = (sort_choice == "遞增 (A-Z)")
        if st.button("🔄 刷新快取", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        st.divider()
        with st.expander("📝 版本更新資訊"): st.markdown(VERSION_HISTORY)

    # --- Tab 4: 反映 (配合 feedback 欄位順序) ---
    with tab_feedback:
        st.markdown("#### 💬 意見反映")
        f_type = st.selectbox("類型", ["功能建議", "錯誤回報", "資料修正", "其他"])
        f_user = st.text_input("您的稱呼 (使用者資訊)", placeholder="匿名")
        f_cont = st.text_area("反映內容 (必填)")
        if st.button("🚀 提交回饋", use_container_width=True):
            if f_cont.strip():
                # 會由 GAS 自動補上時間戳記
                p = {"method": "feedback", "type": f_type, "user": f_user if f_user else "匿名", "content": f_cont}
                res = requests.post(SCRIPT_URL, data=json.dumps(p))
                if "Success" in res.text: st.success("✅ 感謝反映！"); st.balloons()
            else: st.warning("⚠️ 內容不可空白")
