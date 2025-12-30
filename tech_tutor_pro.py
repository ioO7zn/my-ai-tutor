import streamlit as st
import google.generativeai as genai
import pandas as pd
from datetime import datetime

# --- 1. ページ設定 ---
st.set_page_config(
    page_title="Tech Tutor AI (Gemma)",
    page_icon="🎓",
    layout="wide"
)

# --- 2. デザイン完全固定（強制ライトモード） ---
st.markdown("""
<style>
    /* ========================================
       【強制ライトモード化 CSS】
       ダークモード設定を無視して全て白くします
       ========================================
    */

    /* アプリ全体の背景とメインエリア */
    .stApp {
        background-color: #f8f9fa !important; /* 薄いグレー */
    }
    
    /* サイドバーの背景 */
    section[data-testid="stSidebar"] {
        background-color: #ffffff !important; /* 真っ白 */
        border-right: 1px solid #e0e0e0;
    }

    /* 全ての文字色を黒に固定 */
    h1, h2, h3, h4, h5, h6, p, div, span, label, li {
        color: #1f1f1f !important;
        font-family: 'Helvetica Neue', Arial, sans-serif;
    }

    /* === チャットエリアのデザイン === */
    
    /* ユーザーの吹き出し（白） */
    div[data-testid="stChatMessage"]:nth-child(odd) {
        background-color: #ffffff !important;
        border: 1px solid #e0e0e0;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }

    /* AIの吹き出し（薄い青） */
    div[data-testid="stChatMessage"]:nth-child(even) {
        background-color: #f0f7ff !important;
        border: 1px solid #d0e3ff;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    
    /* 吹き出し内のテキストを黒に */
    div[data-testid="stChatMessage"] * {
        color: #1f1f1f !important;
    }

    /* === 復習ノート（Expander）のデザイン === */
    
    .streamlit-expanderHeader {
        background-color: #ffffff !important;
        color: #1f1f1f !important;
        border: 1px solid #ccc !important;
        border-radius: 8px !important;
        font-weight: bold;
    }
    .streamlit-expanderHeader:hover {
        background-color: #f0f8ff !important;
        color: #2196F3 !important;
    }
    .streamlit-expanderContent {
        background-color: #ffffff !important;
        border: 1px solid #ccc;
        border-top: none;
        border-radius: 0 0 8px 8px;
        color: #1f1f1f !important;
    }
    .streamlit-expanderContent p, .streamlit-expanderContent div {
        color: #1f1f1f !important;
    }

    /* === ボタンのデザイン === */
    .stButton > button {
        background-color: #ffffff !important;
        color: #1f1f1f !important;
        border: 1px solid #bbb !important;
        border-radius: 20px !important;
        font-weight: bold !important;
    }
    .stButton > button:hover {
        border-color: #2196F3 !important;
        color: #2196F3 !important;
        background-color: #e3f2fd !important;
    }

    /* コードブロック */
    code {
        color: #d63384 !important;
        background-color: #f0f0f0 !important;
        font-weight: bold;
    }
    
    /* タブ */
    button[data-baseweb="tab"] div { color: #1f1f1f !important; }
    button[aria-selected="true"] div { color: #2196F3 !important; }

</style>
""", unsafe_allow_html=True)

# --- 3. セッション管理 ---
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.messages.append({
        "role": "assistant",
        "content": "こんにちは！Gemmaモデルで学習をサポートします。何について勉強しますか？"
    })

if "study_log" not in st.session_state:
    st.session_state.study_log = []

# --- 4. AIロジック (Gemma固定版) ---
def get_ai_response(user_text, api_key, context, level):
    try:
        genai.configure(api_key=api_key)
        
        # 指示文（プロンプト）の作成
        instruction_text = f"""
        あなたは『{context}』のプロ講師です。生徒レベルは『{level}』。
        
        【構成ルール】
        1. まず、比喩を使って分かりやすく解説する。
        2. 解説の直後に、「理解度チェッククイズ」の問題文だけを出す。
        3. 最後に、区切り文字 `///HIDDEN///` を入れ、その後に正解と解説を書く。
        
        【口調】
        優しく、励ますように。絵文字を使う。
        """
        
        # Gemmaモデルの初期化（System Instructionは使わない）
        model = genai.GenerativeModel('models/gemma-3-27b-it')
        
        # 履歴整形
        history_api = []
        for m in st.session_state.messages:
            role = "user" if m["role"] == "user" else "model"
            clean_text = m["content"].replace("///HIDDEN///", "\n\n【正解】\n")
            history_api.append({"role": role, "parts": [clean_text]})

        # Gemma用に指示文を注入する処理
        if history_api:
            # 履歴がある場合、一番最初のメッセージの先頭に指示文をくっつける
            # これで「先生設定」を思い出させる
            first_msg = history_api[0]['parts'][0]
            if instruction_text not in first_msg: # 重複防止
                 history_api[0]['parts'][0] = instruction_text + "\n\n" + first_msg
            
            chat = model.start_chat(history=history_api)
            response = chat.send_message(user_text)
        else:
            # 履歴がない場合（初回）、今回のメッセージに指示文をくっつけて送る
            chat = model.start_chat(history=[])
            full_prompt = instruction_text + "\n\n" + user_text
            response = chat.send_message(full_prompt)

        return response.text
        
    except Exception as e:
        return f"エラー: {str(e)}\n※APIキーがGemmaに対応していないか、有効ではありません。"

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
    user_level = st.select_slider("📊 現在のレベル", options=["入門", "初級", "中級"], value="初級")
    
    st.divider()
    q_count = sum(1 for m in st.session_state.messages if m["role"] == "user")
    st.write(f"🔥 今日の質問数: {q_count}問")
    st.progress(min(q_count / 10, 1.0))
    st.caption("Using Model: Gemma 3 (27B)")
    
    st.divider()
    if st.button("🗑️ 最初からやり直す", use_container_width=True):
        st.session_state.messages = []
        st.session_state.messages.append({"role": "assistant", "content": "リセットしました！"})
        st.rerun()

# メインエリア
st.title("🎓 Tech Tutor AI")
tab1, tab2 = st.tabs(["💬 チャット学習", "📝 復習ノート"])

# === チャットタブ ===
with tab1:
    # 履歴表示
    for msg in st.session_state.messages:
        role = msg["role"]
        content = msg["content"]
        
        with st.chat_message(role, avatar="🧑‍💻" if role == "user" else "🤖"):
            if role == "assistant" and "///HIDDEN///" in content:
                parts = content.split("///HIDDEN///")
                st.markdown(parts[0]) # 解説と問題
                with st.expander("👀 クリックして正解を見る"):
                    st.markdown(parts[1]) # 答え
            else:
                st.markdown(content)

    st.write("") # 余白

    # AI回答直後のアクション提案
    if st.session_state.messages and st.session_state.messages[-1]["role"] == "assistant":
        st.caption("👇 次のアクションを選んでください")
        col1, col2, col3 = st.columns(3)
        
        next_action = None
        if col1.button("🔍 もっと詳しく", use_container_width=True):
            next_action = "今の説明を、もっと噛み砕いて、別の例えで教えてください。"
        if col2.button("💻 コード例", use_container_width=True):
            next_action = "それを実装する具体的なコード例を書いてください。"
        if col3.button("⚠️ 注意点は？", use_container_width=True):
            next_action = "それを使う時の注意点や、初心者がやりがちなミスは？"
            
        if next_action:
            st.session_state["next_input"] = next_action
            st.rerun()

    # 入力処理
    user_input = st.chat_input("ここに入力...")
    
    if "next_input" in st.session_state:
        user_input = st.session_state.pop("next_input")

    if user_input:
        if not api_key:
            st.error("サイドバーでAPIキーを設定してください")
            st.stop()
            
        st.session_state.messages.append({"role": "user", "content": user_input})
        st.rerun()

# メッセージ生成（最新がユーザーの場合）
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    with tab1:
        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Gemmaが思考中..."):
                last_msg = st.session_state.messages[-1]["content"]
                response_text = get_ai_response(last_msg, api_key, book_context, user_level)
                
                # 表示と保存
                if "///HIDDEN///" in response_text:
                    parts = response_text.split("///HIDDEN///")
                    st.markdown(parts[0])
                    with st.expander("👀 クリックして正解を見る"):
                        st.markdown(parts[1])
                    
                    log_q = last_msg
                    log_a = parts[0]
                    log_ans = parts[1]
                else:
                    st.markdown(response_text)
                    log_q = last_msg
                    log_a = response_text
                    log_ans = "（解説のみ）"

                st.session_state.messages.append({"role": "assistant", "content": response_text})
                
                st.session_state.study_log.append({
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "q": log_q,
                    "a": log_a,
                    "ans": log_ans
                })
                
                st.rerun()

# === 復習ノートタブ ===
with tab2:
    st.info("💡 学習した内容がカード形式で保存されます。")
    
    if st.session_state.study_log:
        for log in reversed(st.session_state.study_log):
            # Expander自体もCSSで白く強制されています
            with st.expander(f"Q. {log['q']}"):
                st.caption(f"日時: {log['time']}")
                
                # 文字色もCSSで黒に強制されています
                st.markdown("**【解説・問題】**")
                st.markdown(log['a'])
                
                if log['ans'] != "（解説のみ）":
                    st.divider()
                    st.markdown("**【正解】**")
                    st.markdown(log['ans'])
        
        st.divider()
        df = pd.DataFrame(st.session_state.study_log)
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 復習データをCSVで保存", csv, "study_log.csv", "text/csv")
    else:
        st.write("まだ履歴がありません。")

