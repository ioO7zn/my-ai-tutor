import streamlit as st
import google.generativeai as genai
import pandas as pd
from datetime import datetime

# --- 1. ページ設定とデザイン ---
st.set_page_config(
    page_title="Tech Tutor AI",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# UIを洗練させるためのカスタムCSS（完全版）
st.markdown("""
<style>
    /* 全体のフォントと背景 */
    .stApp {
        background-color: #f8f9fa;
    }
    
    /* チャット吹き出しのデザイン */
    .stChatMessage {
        background-color: white !important;
        color: #31333F !important;
        border-radius: 15px;
        padding: 15px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        margin-bottom: 10px;
    }

    /* 吹き出し内のすべてのテキスト要素を黒にする */
    .stChatMessage p, .stChatMessage li, .stChatMessage div, .stChatMessage code {
        color: #31333F !important;
    }
    
    /* 復習ノート（Expander）の中身も黒文字にする */
    .streamlit-expanderContent p, .streamlit-expanderContent div, .streamlit-expanderContent li {
        color: #31333F !important;
    }
    .streamlit-expanderHeader {
        color: #31333F !important;
        background-color: white !important;
        border-radius: 10px;
    }

    /* ユーザーのアイコンエリア */
    .stChatMessage[data-testid="stChatMessage"]:nth-child(odd) {
        border-left: 5px solid #4CAF50;
    }
    
    /* AIのアイコンエリア */
    .stChatMessage[data-testid="stChatMessage"]:nth-child(even) {
        border-left: 5px solid #2196F3;
        background-color: #f0f7ff !important;
    }

    /* ボタンのスタイル */
    .stButton>button {
        border-radius: 20px;
        font-weight: bold;
        border: 1px solid #ddd;
    }
    .stButton>button:hover {
        border-color: #2196F3;
        color: #2196F3;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. セッション情報の初期化 ---
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.messages.append({
        "role": "assistant", 
        "content": "こんにちは！今日はどの技術書について学びますか？サイドバーで設定してくださいね。"
    })

if "study_log" not in st.session_state:
    st.session_state.study_log = []

# --- 3. サイドバー（設定エリア） ---
with st.sidebar:
    st.title("⚙️ 設定")
    
    # APIキー管理
    if "GOOGLE_API_KEY" in st.secrets:
        api_key = st.secrets["GOOGLE_API_KEY"]
        st.success("✅ API接続済み")
    else:
        api_key = st.text_input("Google API Key", type="password")
        if not api_key:
            st.warning("⚠️ APIキーを入力してください")
    
    st.markdown("---")
    
    # 学習コンテキスト
    st.subheader("📚 学習テーマ")
    book_context = st.text_input("本のタイトル / 技術名", placeholder="例：Python 1年生", value="Python基礎")
    
    st.subheader("📊 あなたのレベル")
    user_level = st.select_slider(
        "レベルを選択",
        options=["超初心者", "初心者", "中級者", "上級者"],
        value="初心者"
    )
    
    st.markdown("---")

    # 学習ゲージ（質問回数で増える）
    q_count = len([m for m in st.session_state.messages if m["role"] == "user"])
    progress = min(q_count / 10, 1.0) # 10回で満タン
    st.write(f"🔥 今日の学習レベル: Lv.{q_count}")
    st.progress(progress)
    
    st.markdown("---")
    
    # 履歴操作
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🗑️ 会話クリア", use_container_width=True):
            st.session_state.messages = []
            st.rerun()
    with col2:
        if st.button("🔄 全リセット", use_container_width=True):
            st.session_state.messages = []
            st.session_state.study_log = []
            st.rerun()

# --- 4. ロジック関数 ---
def get_ai_response(user_text):
    try:
        genai.configure(api_key=api_key)
        
        system_prompt = f"""
        あなたは親切で優秀な技術メンターです。
        ユーザーは『{book_context}』を学習中の『{user_level}』です。
        
        【回答ルール】
        1. 専門用語は必ず「日常の事物」に例えて解説する（比喩必須）。
        2. 具体的なコード例がある場合は提示する。
        3. 最後に「理解度チェック」として3択クイズを1問出す。
        4. 回答の最後に、ユーザーが次に聞きそうな質問を3つ提案する（形式: [提案: 〇〇について教えて]）。
        """
        
        model = genai.GenerativeModel('models/gemini-flash-latest', system_instruction=system_prompt)
        
        history_for_api = []
        for m in st.session_state.messages:
            if m["role"] == "user":
                history_for_api.append({"role": "user", "parts": [m["content"]]})
            elif m["role"] == "assistant":
                history_for_api.append({"role": "model", "parts": [m["content"]]})

        chat = model.start_chat(history=history_for_api)
        return chat.send_message(user_text, stream=True)
        
    except Exception as e:
        return f"エラー: {str(e)}"

# --- 5. メイン画面 ---
st.title("🎓 Tech Tutor AI")
st.caption(f"現在のモード: {book_context} | レベル: {user_level}")

# タブ切り替え
tab1, tab2 = st.tabs(["💬 メンターとチャット", "📝 復習単語帳"])

# === タブ1：チャット画面 ===
with tab1:
    # メッセージ表示
    for message in st.session_state.messages:
        role = message["role"]
        avatar = "🧑‍💻" if role == "user" else "🤖"
        with st.chat_message(role, avatar=avatar):
            st.markdown(message["content"])

    # 次のアクション（AIからの提案ボタンなど）
    # 直近がAIの回答だった場合、深掘りボタンを出す
    suggested_question = None
    if st.session_state.messages and st.session_state.messages[-1]["role"] == "assistant":
        st.markdown("###### 💡 次はこれを深掘りしてみる？")
        col_s1, col_s2, col_s3 = st.columns(3)
        if col_s1.button("詳しく解説して", use_container_width=True):
            suggested_question = "今の説明を、もっと詳しく、別の例えで教えてください。"
        if col_s2.button("応用例を見せて", use_container_width=True):
            suggested_question = "その技術を使った、もっと実践的な応用コード例を見せてください。"
        if col_s3.button("注意点は？", use_container_width=True):
            suggested_question = "それを使うときに初心者がやりがちな失敗や注意点はありますか？"

    # 通常のクイックアクション
    if not suggested_question:
        st.markdown("###### 👇 質問のショートカット")
        col_q1, col_q2, col_q3, col_q4 = st.columns(4)
        if col_q1.button("これって何？", use_container_width=True):
            suggested_question = f"{book_context}について、初心者向けに概要を教えて"
        elif col_q2.button("コード例", use_container_width=True):
            suggested_question = "具体的なコード例を書いて解説して"
        elif col_q3.button("クイズ出して", use_container_width=True):
            suggested_question = "今の内容について理解度クイズを出して"
        elif col_q4.button("要約して", use_container_width=True):
            suggested_question = "これまでの話を3行で要約して"

    # 入力エリア（一番下）
    prompt = st.chat_input("質問を入力してください...")

    # 処理ロジック（ボタンまたは手入力）
    final_input = None
    if prompt:
        final_input = prompt
    elif suggested_question:
        final_input = suggested_question

    if final_input:
        if not api_key:
            st.error("⚠️ まずAPIキーを設定してください")
            st.stop()

        # ユーザーの入力を表示
        st.session_state.messages.append({"role": "user", "content": final_input})
        with st.chat_message("user", avatar="🧑‍💻"):
            st.markdown(final_input)

        # AIの回答処理
        with st.chat_message("assistant", avatar="🤖"):
            response_container = st.empty()
            full_response = ""
            
            response_stream = get_ai_response(final_input)
            
            if isinstance(response_stream, str):
                if "429" in response_stream:
                    st.error("⚠️ 使いすぎです。少し休憩しましょう☕")
                else:
                    st.error(response_stream)
            else:
                try:
                    for chunk in response_stream:
                        if chunk.text:
                            full_response += chunk.text
                            response_container.markdown(full_response + "▌")
                    
                    response_container.markdown(full_response)
                    
                    st.session_state.messages.append({"role": "assistant", "content": full_response})
                    
                    st.session_state.study_log.append({
                        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "topic": book_context,
                        "question": final_input,
                        "answer": full_response
                    })
                    
                    # 処理が終わったらリランしてボタンの状態をリセット
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"生成エラー: {e}")

# === タブ2：復習ノート ===
with tab2:
    st.header("📝 復習単語帳")
    st.markdown("クリックすると答えが開きます。")
    
    if st.session_state.study_log:
        for i, log in enumerate(reversed(st.session_state.study_log)):
            # Expanderを使ってカード形式にする
            # スタイル適用のため、中身はMarkdownで書く
            with st.expander(f"Q. {log['question']} ({log['date']})"):
                st.markdown(f"**テーマ:** {log['topic']}")
                st.markdown("---") # 区切り線
                st.markdown(log['answer'])
        
        st.divider()
        df = pd.DataFrame(st.session_state.study_log)
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            "📥 ノートをCSVで保存",
            csv,
            "my_study_notes.csv",
            "text/csv",
            key='download-csv'
        )
    else:
        st.info("まだ履歴がありません。チャットタブで質問するとここに保存されます。")


