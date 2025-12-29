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

# UIを洗練させるためのカスタムCSS
st.markdown("""
<style>
    /* 全体のフォントと背景 */
    .stApp {
        background-color: #f8f9fa;
    }
    
    /* チャット吹き出しのデザイン */
    .stChatMessage {
        background-color: white;
        border-radius: 15px;
        padding: 15px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        margin-bottom: 10px;
    }
    
    /* ユーザーのアイコンエリア */
    .stChatMessage[data-testid="stChatMessage"]:nth-child(odd) {
        border-left: 5px solid #4CAF50; /* 緑のアクセント */
    }
    
    /* AIのアイコンエリア */
    .stChatMessage[data-testid="stChatMessage"]:nth-child(even) {
        border-left: 5px solid #2196F3; /* 青のアクセント */
        background-color: #f0f7ff;
    }

    /* ヘッダーの装飾 */
    h1 {
        color: #2c3e50;
        font-family: 'Helvetica Neue', sans-serif;
    }
    
    /* ボタンのスタイル */
    .stButton>button {
        border-radius: 20px;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. セッション情報の初期化 ---
if "messages" not in st.session_state:
    st.session_state.messages = []
    # 最初の挨拶を入れる
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
    
    # 履歴操作
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🗑️ 会話クリア", use_container_width=True):
            st.session_state.messages = []
            st.rerun()
    with col2:
        if st.button("🔄 リセット", use_container_width=True):
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
        4. 口調は丁寧だがフレンドリーに。絵文字を適度に使用する。
        """
        
        # 安定動作する最新Flashモデルを指定
        model = genai.GenerativeModel('models/gemini-flash-latest', system_instruction=system_prompt)
        
        # 過去の会話履歴をAPI形式に変換
        history_for_api = []
        for m in st.session_state.messages:
            if m["role"] == "user":
                history_for_api.append({"role": "user", "parts": [m["content"]]})
            elif m["role"] == "assistant": # StreamlitではassistantだがAPIではmodel
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
        # アイコンの切り替え
        avatar = "🧑‍💻" if role == "user" else "🤖"
        with st.chat_message(role, avatar=avatar):
            st.markdown(message["content"])

    # クイックアクション（入力補助）
    st.markdown("###### 👇 何を聞きますか？")
    col_q1, col_q2, col_q3, col_q4 = st.columns(4)
    if col_q1.button("これって何？", use_container_width=True):
        input_text = f"{book_context}について、初心者向けに概要を教えて"
    elif col_q2.button("コード例", use_container_width=True):
        input_text = "具体的なコード例を書いて解説して"
    elif col_q3.button("クイズ出して", use_container_width=True):
        input_text = "今の内容について理解度クイズを出して"
    elif col_q4.button("要約して", use_container_width=True):
        input_text = "これまでの話を3行で要約して"
    else:
        input_text = None

    # 入力エリア
    if prompt := st.chat_input("質問を入力してください...") or input_text:
        # prompt変数に値が入る（手入力 or ボタン）
        real_prompt = input_text if input_text else prompt

        if not api_key:
            st.error("⚠️ まずAPIキーを設定してください")
            st.stop()

        # ユーザーの入力を表示
        st.session_state.messages.append({"role": "user", "content": real_prompt})
        with st.chat_message("user", avatar="🧑‍💻"):
            st.markdown(real_prompt)

        # AIの回答処理
        with st.chat_message("assistant", avatar="🤖"):
            response_container = st.empty()
            full_response = ""
            
            response_stream = get_ai_response(real_prompt)
            
            # エラー処理
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
                    
                    # 履歴に保存
                    st.session_state.messages.append({"role": "assistant", "content": full_response})
                    
                    # 復習ログに保存（質問と回答のペア）
                    st.session_state.study_log.append({
                        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "topic": book_context,
                        "question": real_prompt,
                        "answer": full_response
                    })
                    
                except Exception as e:
                    st.error(f"生成エラー: {e}")

# === タブ2：復習ノート ===
with tab2:
    st.header("📝 復習単語帳")
    st.markdown("チャットした内容が自動でカード化されます。クリックして答え合わせしましょう！")
    
    if st.session_state.study_log:
        # ログを新しい順に表示
        for i, log in enumerate(reversed(st.session_state.study_log)):
            # Expanderを使ってカード形式にする
            with st.expander(f"Q. {log['question']} ({log['date']})"):
                st.markdown(f"**テーマ:** {log['topic']}")
                st.divider()
                st.markdown(log['answer'])
        
        st.divider()
        # CSVダウンロード機能
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




