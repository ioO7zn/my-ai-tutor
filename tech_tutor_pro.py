import streamlit as st
import google.generativeai as genai
import pandas as pd
from datetime import datetime

# --- 1. ページ設定とデザイン ---
st.set_page_config(
    page_title="Tech Tutor AI",
    page_icon="🎓",
    layout="wide"
)

# カスタムCSSで見た目を少し整える
st.markdown("""
<style>
    .stChatMessage {border-radius: 10px; padding: 10px;}
    .reportview-container {background: #f0f2f6}
</style>
""", unsafe_allow_html=True)

# --- 2. セッション情報の初期化 ---
# チャット履歴の保存場所
if "messages" not in st.session_state:
    st.session_state.messages = []

# 学習ログ（復習用）の保存場所
if "study_log" not in st.session_state:
    st.session_state.study_log = []

# --- 3. サイドバー（設定エリア） ---
with st.sidebar:
    st.header("⚙️ 学習環境設定")
    
    # Secretsにキーがあればそれを使い、なければ入力欄を出す
    if "GOOGLE_API_KEY" in st.secrets:
        api_key = st.secrets["GOOGLE_API_KEY"]
    else:
        api_key = st.sidebar.text_input("Google API Key", type="password")
    
    st.divider()
    
    # コンテキスト設定
    st.subheader("📚 今の学習テーマ")
    book_context = st.text_input("読んでいる本の名前・技術", placeholder="例：React入門、ゼロから作るDeep Learning")
    
    user_level = st.select_slider(
        "あなたの理解度レベル",
        options=["小学生レベル", "初心者", "中級者", "専門家"],
        value="初心者"
    )
    
    st.divider()
    
    # 履歴クリアボタン
    if st.button("🗑️ 会話履歴をクリア"):
        st.session_state.messages = []
        st.rerun()

# --- 4. メインロジック関数 ---
def get_ai_response(user_text):
    """Gemini APIを呼び出して回答を生成する関数"""
    try:
        genai.configure(api_key=api_key)
        # 思考の連鎖や役割定義を行うシステムプロンプト
        system_prompt = f"""
        あなたはプロフェッショナルな技術教育者です。
        現在、ユーザーは『{book_context}』について学習しています。
        ターゲット読者レベル：『{user_level}』。
        
        以下のルールを守って回答してください：
        1. ユーザーが入力した用語や概念を、指定された本の文脈に合わせて解説する。
        2. 専門用語はなるべく噛み砕き、比喩（例え話）を必ず一つ入れる。
        3. 必要であればコード例（Pythonなど）を提示する。
        4. マークダウン形式で見やすく出力する。
        5. 回答の最後に、理解を深めるための「ミニクイズ」を1問出す。
        """
        
        model = genai.GenerativeModel('gemini-pro', system_instruction=system_prompt)
        
        # 会話履歴を含めて送信（文脈維持のため）
        chat = model.start_chat(history=[
            {"role": m["role"], "parts": [m["content"]]} 
            for m in st.session_state.messages if m["role"] != "system"
        ])
        
        response = chat.send_message(user_text, stream=True)
        return response
    except Exception as e:
        return f"エラーが発生しました: {e}"

# --- 5. アプリケーション画面構成 ---
st.title("🎓 Tech Tutor AI")
st.caption(f"Context: {book_context if book_context else '未設定'} | Level: {user_level}")

# タブで機能を切り替え
tab1, tab2 = st.tabs(["💬 学習チャット", "📝 復習ノート"])

with tab1:
    # 過去のメッセージを表示
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # ユーザー入力エリア
    if prompt := st.chat_input("わからない単語やコードを入力..."):
        if not api_key:
            st.error("サイドバーでAPIキーを設定してください。")
            st.stop()

        # ユーザーのメッセージを表示・保存
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # AIの回答を表示・保存
        with st.chat_message("assistant"):
            response_container = st.empty()
            full_response = ""
            
            # ストリーミング表示（文字がカタカタ出る演出）
            response_stream = get_ai_response(prompt)
            
            # エラー文字列が返ってきた場合の処理
            if isinstance(response_stream, str):
                response_container.error(response_stream)
            else:
                for chunk in response_stream:
                    if chunk.text:
                        full_response += chunk.text
                        response_container.markdown(full_response + "▌")
                response_container.markdown(full_response)
                
                # メッセージ履歴に追加
                st.session_state.messages.append({"role": "model", "content": full_response})
                
                # 復習ログに追加（質問と回答の要約などを保存する想定）
                st.session_state.study_log.append({
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "question": prompt,
                    "context": book_context
                })

with tab2:
    st.header("📝 復習ノート")
    st.write("質問した履歴がここに蓄積されます。")
    
    if st.session_state.study_log:
        df = pd.DataFrame(st.session_state.study_log)
        st.dataframe(df, use_container_width=True)
        
        # CSVダウンロードボタン
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 学習ログをCSVでダウンロード",
            data=csv,
            file_name='my_study_log.csv',
            mime='text/csv',
        )
    else:

        st.info("まだ質問履歴がありません。チャットタブで質問してみましょう！")


