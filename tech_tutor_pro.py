import streamlit as st
import google.generativeai as genai
import pandas as pd
from datetime import datetime

# --- 1. ページ設定 ---
st.set_page_config(
    page_title="Tech Tutor AI",
    page_icon="🎓",
    layout="wide"
)

# --- 2. デザイン（ホワイトモード完全固定） ---
st.markdown("""
<style>
    .stApp { background-color: #f8f9fa !important; }
    section[data-testid="stSidebar"] { background-color: #ffffff !important; border-right: 1px solid #e0e0e0; }
    h1, h2, h3, h4, h5, h6, p, div, span, label, li { color: #1f1f1f !important; }
    
    /* チャットエリア */
    div[data-testid="stChatMessage"]:nth-child(odd) {
        background-color: #ffffff !important;
        border: 1px solid #e0e0e0;
        border-radius: 12px;
        padding: 20px;
    }
    div[data-testid="stChatMessage"]:nth-child(even) {
        background-color: #f0f7ff !important;
        border: 1px solid #d0e3ff;
        border-radius: 12px;
        padding: 20px;
    }
    div[data-testid="stChatMessage"] * { color: #1f1f1f !important; }

    /* 復習ノート */
    .streamlit-expanderHeader {
        background-color: #ffffff !important;
        color: #1f1f1f !important;
        border: 1px solid #ccc !important;
        border-radius: 8px !important;
    }
    .streamlit-expanderContent {
        background-color: #ffffff !important;
        border: 1px solid #ccc;
        border-top: none;
        color: #1f1f1f !important;
    }
    
    /* ボタン */
    .stButton > button {
        background-color: #ffffff !important;
        color: #1f1f1f !important;
        border: 1px solid #bbb !important;
        font-weight: bold !important;
        border-radius: 20px !important;
    }
    .stButton > button:hover {
        border-color: #2196F3 !important;
        color: #2196F3 !important;
        background-color: #e3f2fd !important;
    }
    code { color: #d63384 !important; background-color: #f0f0f0 !important; }
</style>
""", unsafe_allow_html=True)

# --- 3. セッション管理 ---
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "こんにちは！モデルを選んで学習を始めましょう。"}]

if "study_log" not in st.session_state:
    st.session_state.study_log = []

# --- 4. AIロジック (Gemmaのエラー回避対応版) ---
def get_ai_response(user_text, api_key, context, level, model_name):
    try:
        genai.configure(api_key=api_key)
        
        # システムプロンプト（AIへの命令文）
        system_prompt_text = f"""
        あなたは『{context}』のプロ講師です。生徒レベルは『{level}』。
        
        【構成ルール】
        1. まず、比喩を使って分かりやすく解説する。
        2. 解説の直後に、「理解度チェッククイズ」の問題文だけを出す。
        3. 最後に、区切り文字 `///HIDDEN///` を入れ、その後に正解と解説を書く。
        """
        
        # 履歴の準備
        history_api = []
        for m in st.session_state.messages:
            role = "user" if m["role"] == "user" else "model"
            clean_text = m["content"].replace("///HIDDEN///", "\n\n【正解】\n")
            history_api.append({"role": role, "parts": [clean_text]})

        # ★ここが重要：モデルによって設定方法を変える
        if "gemma" in model_name.lower():
            # Gemmaの場合: system_instructionが使えないので、無理やり会話の最初に混ぜる
            model = genai.GenerativeModel(model_name)
            
            # 履歴がある場合は、最初のメッセージに命令を混ぜる
            if history_api:
                # 最初のメッセージの先頭に命令を追加
                first_msg = history_api[0]['parts'][0]
                history_api[0]['parts'][0] = system_prompt_text + "\n\n" + first_msg
            else:
                # 履歴がない場合（初回）は、ユーザー入力に混ぜる
                user_text = system_prompt_text + "\n\n" + user_text
        else:
            # Geminiの場合: 正規の機能を使う
            model = genai.GenerativeModel(model_name, system_instruction=system_prompt_text)

        chat = model.start_chat(history=history_api)
        response = chat.send_message(user_text)
        return response.text
        
    except Exception as e:
        return f"エラー: {str(e)}\n(モデル名が間違っているか、APIキーが対応していません)"

# --- 5. アプリ画面構成 ---

# サイドバー
with st.sidebar:
    st.title("⚙️ 設定")
    if "GOOGLE_API_KEY" in st.secrets:
        api_key = st.secrets["GOOGLE_API_KEY"]
    else:
        api_key = st.text_input("Google API Key", type="password")
    
    st.divider()
    book_context = st.text_input("📚 本・技術名", value="Python基礎")
    user_level = st.select_slider("📊 レベル", options=["入門", "初級", "中級"], value="初級")
    
    st.divider()
    
    # ★モデル選択
    st.write("🧠 AIモデル選択")
    model_option = st.selectbox(
        "使用するモデル",
        (
            "Gemini 1.5 Flash (高速・推奨)", 
            "Gemini 1.5 Pro (高精度)", 
            "Gemma 3 (27B)"
        )
    )
    
    # モデルIDの割り当て
    if "Flash" in model_option:
        current_model = "models/gemini-1.5-flash-latest"
    elif "Pro" in model_option:
        current_model = "models/gemini-1.5-pro-latest"
    elif "Gemma" in model_option:
        # ※もしGemma 3を使いたい場合は、ここのIDを書き換えてください
        # 例: "models/gemma-3-27b-it" (APIで有効な場合のみ)
        current_model = "models/gemma-3-27b-it"

    # もし手動で試したい場合用（デバッグ）
    use_custom = st.checkbox("モデルIDを手動入力する")
    if use_custom:
        current_model = st.text_input("モデルIDを入力", value=current_model)

    st.caption(f"使用中ID: {current_model}")

    st.divider()
    if st.button("🗑️ 最初からやり直す", use_container_width=True):
        st.session_state.messages = [{"role": "assistant", "content": "リセットしました！"}]
        st.rerun()

# メインエリア
st.title("🎓 Tech Tutor AI")
tab1, tab2 = st.tabs(["💬 チャット学習", "📝 復習ノート"])

# === チャットタブ ===
with tab1:
    for msg in st.session_state.messages:
        role = msg["role"]
        content = msg["content"]
        with st.chat_message(role, avatar="🧑‍💻" if role == "user" else "🤖"):
            if role == "assistant" and "///HIDDEN///" in content:
                parts = content.split("///HIDDEN///")
                st.markdown(parts[0])
                with st.expander("👀 クリックして正解を見る"):
                    st.markdown(parts[1])
            else:
                st.markdown(content)

    st.write("") 

    # アクション提案
    if st.session_state.messages and st.session_state.messages[-1]["role"] == "assistant":
        st.caption("👇 次のアクション")
        col1, col2, col3 = st.columns(3)
        if col1.button("🔍 もっと詳しく", use_container_width=True):
            st.session_state["next_input"] = "今の説明を、もっと噛み砕いて、別の例えで教えてください。"
            st.rerun()
        if col2.button("💻 コード例", use_container_width=True):
            st.session_state["next_input"] = "それを実装する具体的なコード例を書いてください。"
            st.rerun()
        if col3.button("⚠️ 注意点は？", use_container_width=True):
            st.session_state["next_input"] = "初心者がやりがちなミスは？"
            st.rerun()

    # 入力
    user_input = st.chat_input("ここに入力...")
    if "next_input" in st.session_state:
        user_input = st.session_state.pop("next_input")

    if user_input:
        if not api_key:
            st.error("APIキーを設定してください")
            st.stop()
        st.session_state.messages.append({"role": "user", "content": user_input})
        st.rerun()

if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    with tab1:
        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("AIが思考中..."):
                last_msg = st.session_state.messages[-1]["content"]
                response_text = get_ai_response(last_msg, api_key, book_context, user_level, current_model)
                
                if "///HIDDEN///" in response_text:
                    parts = response_text.split("///HIDDEN///")
                    st.markdown(parts[0])
                    with st.expander("👀 クリックして正解を見る"):
                        st.markdown(parts[1])
                    log_a = parts[0]
                    log_ans = parts[1]
                else:
                    st.markdown(response_text)
                    log_a = response_text
                    log_ans = "（解説のみ）"

                st.session_state.messages.append({"role": "assistant", "content": response_text})
                st.session_state.study_log.append({
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "q": last_msg, "a": log_a, "ans": log_ans
                })
                st.rerun()

# === 復習ノートタブ ===
with tab2:
    if st.session_state.study_log:
        for log in reversed(st.session_state.study_log):
            with st.expander(f"Q. {log['q']}"):
                st.caption(f"日時: {log['time']}")
                st.markdown("**【解説】**")
                st.markdown(log['a'])
                if log['ans'] != "（解説のみ）":
                    st.divider()
                    st.markdown("**【正解】**")
                    st.markdown(log['ans'])
        st.divider()
        df = pd.DataFrame(st.session_state.study_log)
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 CSV保存", csv, "study_log.csv", "text/csv")
