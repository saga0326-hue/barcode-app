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

# --- 核心：強制九宮格鍵盤腳本 ---
def force_numeric_pad():
    components.html(
        """
        <script>
            const fixInputs = () => {
                var inputs = window.parent.document.querySelectorAll("input[type='number']");
                for (var i = 0; i < inputs.length; i++) {
                    inputs[i].setAttribute("inputmode", "numeric");
                    inputs[i].setAttribute("pattern", "[0-9]*");
                }
            };
            fixInputs();
            setTimeout(fixInputs, 1000);
            setTimeout(fixInputs, 3000);
        </script>
        """,
        height=0,
    )

# 2. 數據讀取
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
st.markdown("### 🛡️ 團隊共享條碼系統")
force_numeric_pad()

df_main = fetch_data(DATA_URL)
df_cat = fetch_data(CAT_URL)

if isinstance(df_main, pd.DataFrame):
    # 修改點：在 Tabs 中新增 "💬 意見反映"
    tab_search, tab_add, tab_settings, tab_feedback = st.tabs(["🔍 快速搜尋", "➕ 新增品項", "⚙️ 設定", "💬 意見反映"])

    # --- Tab 1: 搜尋 (略，保持原樣) ---
    with tab_search:
        unique_types = sorted([str(t) for t in df_cat['類型'].unique() if t and t != 'nan'])
        selected_type = st.selectbox("📂 選擇類別", ["全部"] + unique_types)
        search_name = st.text_input("📝 品名關鍵字")
        search_code_num = st.number_input("🔢 條碼搜尋", step=1, value=None)
        search_code = str(search_code_num) if search_code_num is not None else ""
        
        # 搜尋邏輯與排序顯示... (保持原樣)
        sort_choice = "遞增 (A-Z)" # 預設預留
        is_ascending = True

        if (search_name != "") or (search_code != "") or (selected_type != "全部"):
            work_df = df_main.copy() if selected_type == "全部" else df_cat[df_cat['類型'] == selected_type].copy()
            if search_name: work_df = work_df[work_df['品名'].str.contains(search_name, na=False, case=False)]
            if search_code: work_df = work_df[work_df['條碼'].str.contains(search_code, na=False)]
            work_df = work_df.sort_values(by='品名', ascending=is_ascending).head(50)
            for _, row in work_df.iterrows():
                with st.container(border=True):
                    st.write(f"**{row['品名']}** ({row.get('條碼','')})")

    # --- Tab 2: 新增品項 (保持原樣) ---
    with tab_add:
        st.subheader("➕ 新增商品")
        new_name = st.text_input("商品品名")
        new_bc_num = st.number_input("商品條碼", step=1, value=None)
        if st.button("確認送出條碼"):
            if new_name and new_bc_num:
                payload = {"method": "add_barcode", "type": "預設", "name": new_name, "barcode": str(new_bc_num)}
                res = requests.post(SCRIPT_URL, data=json.dumps(payload))
                st.success("寫入成功")
                st.cache_data.clear()

    # --- Tab 3: 設定 (略) ---
    with tab_settings:
        st.write("設定頁面")

    # --- Tab 4: 意見反映 (新功能) ---
    with tab_feedback:
        st.markdown("#### 💬 意見反映與錯誤回報")
        st.caption("您的建議是我們進步的動力，請填寫下方資訊：")
        
        fb_type = st.selectbox("反映類型", ["功能建議", "錯誤回報", "資料修正", "其他"])
        fb_user = st.text_input("您的稱呼 (選填)", placeholder="例如：小明")
        fb_content = st.text_area("反映內容 (必填)", placeholder="請詳細描述您的問題或建議...")
        
        fb_status = st.empty()
        
        if st.button("🚀 提交意見", use_container_width=True):
            if fb_content:
                fb_status.info("⏳ 提交中...")
                # 傳送 method="feedback" 讓 GAS 辨別要寫入哪個 Sheet
                fb_payload = {
                    "method": "feedback",
                    "type": fb_type,
                    "user": fb_user if fb_user else "匿名",
                    "content": fb_content
                }
                try:
                    res = requests.post(SCRIPT_URL, data=json.dumps(fb_payload), timeout=15)
                    fb_status.empty()
                    if "Success" in res.text:
                        st.success("✅ 我們已收到您的寶貴意見，謝謝！")
                        # 提交後清空內容的簡單做法是 rerun
                        st.balloons()
                    else:
                        st.error(f"❌ 提交失敗：{res.text}")
                except Exception as e:
                    fb_status.empty()
                    st.error(f"❌ 連線失敗：{str(e)}")
            else:
                st.warning("⚠️ 請填寫反映內容後再提交")

else:
    st.error("⚠️ 資料源連線失敗")
