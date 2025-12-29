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

# --- 2. デザイン完全固定（どんな環境でも崩れないCSS） ---
st.markdown("""
<style>
    /* アプリ全体の背景（薄いグレーで統一） */
    .stApp {
        background-color: #f0f2f6;
    }

    /* === チャットメッセージ（重要） === */
    /* どんな環境でも「白背景・黒文字」または「薄青背景・黒文字」にする */
    
    /* 1. ユーザーのメッセージ（白） */
    div[data-testid="stChatMessage"]:nth-child(odd) {
        background-color: #ffffff !important;
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        padding: 15px;
        color: #1f1f1f !important; /* 文字色は濃いグレー */
    }

    /* 2. AIのメッセージ（薄い青） */
    div[data-testid="stChatMessage"]:nth-child(even) {
        background-color: #f0f7ff !important;
        border: 1px solid #d0e3ff;
        border-radius: 10px;
        padding: 15px;
        color: #1f1f1f !important;
    }

    /* 3. メッセージ内の全てのテキスト要素を強制的に黒にする */
    /* これがないとダークモード時に文字が白くなり見えなくなる */
    div[data-testid="stChatMessage"] p, 
    div[data-testid="stChatMessage"] div, 
    div[data-testid="stChatMessage"] h1, 
    div[data-testid="stChatMessage"] h2, 
    div[data-testid="stChatMessage"] h3, 
    div[data-testid="stChatMessage"] li {
        color: #1f1f1f !important;
    }

    /* === ボタンのデザイン === */
    /* デフォルトの塗りつぶしをやめて、見やすい枠線ボタンスタイルにする */
    .stButton > button {
        background-color: #ffffff !important;
        color: #1f1f1f !important;
        border: 1px solid #ccc !important;
        border-radius: 20px !important;
        font-weight: bold !important;
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        border-color: #2196F3 !important;
        color: #2196F3 !important;
        background-color: #e3f2fd !important;
    }

    /* === アコーディオン（正解を見る部分） === */
    .streamlit-expanderHeader {
        background-color: #ffffff !important;
        color: #1f1f1f !important;
        border: 1px solid #ddd !important;
        border-radius: 5px;
    }
    .streamlit-expanderContent {
        background-color: #fafafa !important;
        border: 1px solid #ddd;
        border-top: none;
        color: #1f1f1f !important;
    }
    .streamlit-expanderContent p {
        color: #1f1f1f !important;
    }

    /* コードブロックの調整 */
    code {
        color: #d63384 !important; /* ピンク系で見やすく */
        font-family: monospace;
    }
</style>
""", unsafe_allow_html=True)

# --- 3. セッション管理 ---
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.messages.append({
        "role": "assistant",
        "content": "こんにちは！学習をサポートします。何について勉強しますか？"
    })

if "study_log" not in st.session_state:
    st.session_state.study_log = []

# --- 4. AIロジック ---
def get_ai_response(user_text, api_key, context, level):
    try:
        genai.configure(api_key=api_key)
        
        system_prompt = f"""
        あなたは『{context}』のプロ講師です。生徒レベルは『{level}』。
        
        【構成ルール】
        1. まず、比喩を使って分かりやすく解説する。
        2. 解説の直後に、「理解度チェッククイズ」の問題文だけを出す。
        3. 最後に、区切り文字 `///HIDDEN///` を入れ、その後に正解と解説を書く。
        
        【口調】
        優しく、励ますように。絵文字を使う。
        """
        
        model = genai.GenerativeModel('models/gemini-flash-latest', system_instruction=system_prompt)
        
        # 履歴整形
        history_api = []
        for m in st.session_state.messages:
            role = "user" if m["role"] == "user" else "model"
            # 隠し文字を除去して履歴に入れる
            clean_text = m["content"].replace("///HIDDEN///", "\n\n【正解】\n")
            history_api.append({"role": role, "parts": [clean_text]})

        chat = model.start_chat(history=history_api)
        response = chat.send_message(user_text)
        return response.text
        
    except Exception as e:
        return f"エラー: {str(e)}"

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
    # 経験値バー
    q_count = sum(1 for m in st.session_state.messages if m["role"] == "user")
    st.write(f"🔥 今日の質問数: {q_count}問")
    st.progress(min(q_count / 10, 1.0))
    
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
    
    # ボタン入力があればそれを優先
    if "next_input" in st.session_state:
        user_input = st.session_state.pop("next_input")

    if user_input:
        if not api_key:
            st.error("サイドバーでAPIキーを設定してください")
            st.stop()
            
        # ユーザー入力を表示
        st.session_state.messages.append({"role": "user", "content": user_input})
        st.rerun()

# メッセージ生成（最新がユーザーの場合）
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    with tab1:
        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("考え中..."):
                last_msg = st.session_state.messages[-1]["content"]
                response_text = get_ai_response(last_msg, api_key, book_context, user_level)
                
                # 表示
                if "///HIDDEN///" in response_text:
                    parts = response_text.split("///HIDDEN///")
                    st.markdown(parts[0])
                    with st.expander("👀 クリックして正解を見る"):
                        st.markdown(parts[1])
                    
                    # ログ保存用
                    log_q = last_msg
                    log_a = parts[0]
                    log_ans = parts[1]
                else:
                    st.markdown(response_text)
                    log_q = last_msg
                    log_a = response_text
                    log_ans = "（解説のみ）"

                # 履歴保存
                st.session_state.messages.append({"role": "assistant", "content": response_text})
                
                # 復習ログ保存
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
            with st.expander(f"Q. {log['q']}"):
                st.caption(f"日時: {log['time']}")
                st.markdown("**【解説・問題】**")
                st.markdown(log['a'])
                if log['ans'] != "（解説のみ）":
                    st.divider()
                    st.markdown("**【正解】**")
                    st.markdown(log['ans'])
        
        st.divider()
        # CSVダウンロード
        df = pd.DataFrame(st.session_state.study_log)
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 復習データをCSVで保存", csv, "study_log.csv", "text/csv")
    else:
        st.write("まだ履歴がありません。")
