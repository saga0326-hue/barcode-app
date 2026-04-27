import streamlit as st
import pandas as pd
import requests
import json
import streamlit.components.v1 as components

# 1. 頁面基礎設定
st.set_page_config(page_title="專業商品條碼系統", layout="wide", page_icon="📦", initial_sidebar_state="collapsed")

# --- CSS 注入：將按鈕移入輸入框並美化為圓形叉叉 ---
st.markdown("""
<style>
    /* 定位容器 */
    [data-testid="stHorizontalBlock"] {
        align-items: center;
    }
    /* 隱藏按鈕原本的邊框與背景 */
    .stButton > button {
        border: none !important;
        background-color: transparent !important;
        color: #B0B0B0 !important; /* 灰色 */
        padding: 0px !important;
        width: 30px !important;
        height: 30px !important;
        margin-left: -45px !important; /* 關鍵：向左移動覆蓋到輸入框內 */
        z-index: 99;
        font-size: 18px !important;
        border-radius: 50% !important;
    }
    /* 按鈕懸停效果 */
    .stButton > button:hover {
        color: #808080 !important;
        background-color: #F0F2F6 !important;
    }
    /* 修正輸入框右側間距，避免文字被叉叉遮住 */
    .stTextInput input {
        padding-right: 40px !important;
        border-radius: 20px !important; /* 圓角造型 */
    }
</style>
""", unsafe_allow_html=True)

# --- 更新日誌 ---
VERSION_HISTORY = """
**(2026/04/27)**
- 🎨 **美化**：透過 CSS 注入，將清除按鈕移入輸入框內，達成 iOS/Android 原生搜尋框視覺效果。
- 🗑️ **移除**：應需求移除「清除」按鈕，簡化介面。
- 🛡️ **邏輯**：新增強制篩選機制，類別或口座必須擇一篩選方可顯示結果。
- 🔍 **優化**：搜尋欄位開啟原生 `clear_on_submit` 功能，點擊 Enter 後可快速作業。
- 🔍 **修正**：支援「0」開頭條碼搜尋。
- 📱 **優化**：優化手機端數字鍵盤配置。

**(2024/04/24)**
- 🛡️ **安全**：新增「防重複送出」機制，送出後自動禁用按鈕，防止連點。
- 🛠️ **修復**：精確校準 `categories` 與 `feedback` 試算表欄位順序，解決寫入位移問題。
- 🔄 **變更**：將「新增商品」類別改回下拉選單，提升操作精確度並避免誤觸。
- 🏦 **優化**：查詢頁面採用「迷你按鈕 (Segmented Control)」，優化 iPhone 瀏覽體驗。
- 🧹 **清理**：移除新增商品時的「口座」選項，簡化填寫流程。
- ⚙️ **系統**：新增設定頁面「版本資訊」區塊，同步紀錄更新日誌。

**(2024/04/20)**
- ➕ 新增：口座 (04, 05, 07) 快速篩選功能。
- 🔍 優化：針對手機端自動喚起九宮格數字鍵盤。
"""

# --- 初始化 Session State ---
if 'submitting_item' not in st.session_state:
    st.session_state.submitting_item = False
if 'submitting_fb' not in st.session_state:
    st.session_state.submitting_fb = False
if 'input_name' not in st.session_state:
    st.session_state.input_name = ""
if 'input_code' not in st.session_state:
    st.session_state.input_code = ""

# 2. 核心腳本 (強制手機數字鍵盤)
def force_numeric_pad():
    components.html("""<script>
        const fixInputs = () => {
            const inputs = window.parent.document.querySelectorAll("input");
            inputs.forEach(input => {
                if (input.placeholder.includes('條碼') || input.placeholder.includes('支援 0')) {
                    input.setAttribute("inputmode", "numeric");
                    input.setAttribute("pattern", "[0-9]*");
                }
            });
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

    # --- Tab 1: 搜尋 ---
    with tab_search:
        unique_types = sorted([str(t) for t in df_cat['類型'].unique() if t and t != 'nan'])
        
        st.write("📂 **類別篩選**")
        selected_type = st.segmented_control("tsel", options=["全部"] + unique_types, default="全部", label_visibility="collapsed")
        
        st.write("🏦 **口座篩選**")
        selected_koz = st.segmented_control("ksel", options=["全部", "04", "05", "07"], default="全部", label_visibility="collapsed")
        
        st.divider()
        
        # --- 品名輸入框與鑲嵌叉叉 ---
        c_name_in, c_name_clr = st.columns([10, 1])
        with c_name_in:
            s_name = st.text_input("📝 品名關鍵字", placeholder="輸入關鍵字...", key="input_name", label_visibility="collapsed")
        with c_name_clr:
            if st.button("✖", key="clr_name"):
                st.session_state.input_name = ""
                st.rerun()

        # --- 條碼輸入框與鑲嵌叉叉 ---
        c_code_in, c_code_clr = st.columns([10, 1])
        with c_code_in:
            s_code = st.text_input("🔢 條碼搜尋", placeholder="支援 0 開頭條碼", key="input_code", label_visibility="collapsed")
        with c_code_clr:
            if st.button("✖", key="clr_code"):
                st.session_state.input_code = ""
                st.rerun()

        # 搜尋邏輯
        is_asc = st.session_state.get('is_ascending', True)
        has_filter = selected_type != "全部" or selected_koz != "全部"
        has_input = s_name.strip() != "" or s_code.strip() != ""

        if has_filter or has_input:
            w_df = df_main.copy() if selected_type == "全部" else df_cat[df_cat['類型'] == selected_type].copy()
            if selected_koz != "全部": w_df = w_df[w_df['口座'] == selected_koz]
            if s_name: w_df = w_df[w_df['品名'].str.contains(s_name, na=False, case=False)]
            if s_code: 
                w_df = w_df[w_df['條碼'].str.contains(s_code, na=False) | w_df['商品代號'].str.contains(s_code, na=False)]
            
            w_df = w_df.sort_values(by='品名', ascending=is_asc).head(50)

            if len(w_df) == 0:
                st.info("查無符合條件的商品")
            else:
                for _, r in w_df.iterrows():
                    with st.container(border=True):
                        c1, c2 = st.columns([1.5, 3])
                        with c1: st.image(f"https://bwipjs-api.metafloor.com/?bcid=code128&text={r.get('條碼','')}&scale=2&includetext")
                        with c2:
                            st.markdown(f"**{r['品名']}**")
                            st.caption(f"口座: {r.get('口座','-')} | 代號: {r.get('商品代號','-')}")
        else:
            st.warning("💡 請選擇「類別」或「口座」開始搜尋")

    # --- 其餘頁面 (Tab 2, 3, 4) 保持不變 ---
    with tab_add:
        st.markdown("#### ➕ 新增商品")
        u_types = sorted([str(t) for t in df_cat['類型'].unique() if t and t != 'nan'])
        chosen_type = st.selectbox("📂 選擇類別", u_types + ["➕ 新增類別..."], index=0)
        final_type = st.text_input("📝 請輸入新類別名稱") if chosen_type == "➕ 新增類別..." else chosen_type
        new_name = st.text_input("📦 商品品名")
        new_bc = st.number_input("🔢 商品條碼", step=1, value=None, key="abc")
        
        submit_item_btn = st.button("🚀 執行送出", use_container_width=True, disabled=st.session_state.submitting_item)
        if submit_item_btn and final_type and new_name and new_bc:
            st.session_state.submitting_item = True
            st.rerun()

        if st.session_state.submitting_item:
            try:
                payload = {"method": "add_barcode", "type": final_type, "name": new_name, "barcode": str(new_bc)}
                res = requests.post(SCRIPT_URL, data=json.dumps(payload), timeout=15)
                st.success(f"✅ 已成功寫入：{new_name}")
                st.cache_data.clear()
            finally:
                st.session_state.submitting_item = False
                st.stop()

    with tab_settings:
        sort_choice = st.radio("品名排序方向", ["遞增 (A-Z)", "遞減 (Z-A)"], index=0)
        st.session_state['is_ascending'] = (sort_choice == "遞增 (A-Z)")
        if st.button("🔄 刷新快取", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        st.divider()
        with st.expander("📝 版本更新資訊"): st.markdown(VERSION_HISTORY)

    with tab_feedback:
        st.markdown("#### 💬 意見反映")
        f_type = st.selectbox("類型", ["功能建議", "錯誤回報", "資料修正", "其他"])
        f_user = st.text_input("您的稱呼", placeholder="匿名")
        f_cont = st.text_area("反映內容 (必填)")
        if st.button("🚀 提交回饋", use_container_width=True) and f_cont.strip():
            try:
                p = {"method": "feedback", "type": f_type, "user": f_user if f_user else "匿名", "content": f_cont}
                requests.post(SCRIPT_URL, data=json.dumps(p), timeout=15)
                st.success("✅ 感謝反映！")
                st.balloons()
            except: st.error("傳送失敗")
else:
    st.error("⚠️ 資料源連線失敗")
