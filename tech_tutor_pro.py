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

# カスタムCSS
st.markdown("""
<style>
    .stChatMessage {border-radius: 10px; padding: 10px;}
    .reportview-container {background: #f0f2f6}
</style>
""", unsafe_allow_html=True)

# --- 2. セッション情報の初期化 ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "study_log" not in st.session_state:
    st.session_state.study_log = []

# --- 3. サイドバー（設定エリア） ---
with st.sidebar:
    st.header("⚙️ 学習環境設定")
    
    # Secretsまたは入力からキーを取得
    if "GOOGLE_API_KEY" in st.secrets:
        api_key = st.secrets["GOOGLE_API_KEY"]
        st.success("✅ APIキー読込完了")
    else:
        api_key = st.sidebar.text_input("Google API Key", type="password")
    
    st.divider()
    
    # コンテキスト設定
    st.subheader("📚 今の学習テーマ")
    book_context = st.text_input("読んでいる本の名前・技術", placeholder="例：React入門")
    
    user_level = st.select_slider(
        "あなたの理解度レベル",
        options=["小学生レベル", "初心者", "中級者", "専門家"],
        value="初心者"
    )
    
    st.divider()
    
    if st.button("🗑️ 会話履歴をクリア"):
        st.session_state.messages = []
        st.rerun()

# --- 4. メインロジック関数 ---
def get_ai_response(user_text):
    """Gemini APIを呼び出して回答を生成する関数"""
    try:
        # APIキーの設定
        genai.configure(api_key=api_key)
        
        # システムプロンプト
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
        
        # ★ここを修正：モデルを自動検出せず、文字列で直接指定します
        # これにより "2.5-pro" などの使えないモデルが選ばれるのを防ぎます
        target_model = 'gemini-1.5-flash'
        
        model = genai.GenerativeModel(target_model, system_instruction=system_prompt)
        
        chat = model.start_chat(history=[
            {"role": m["role"], "parts": [m["content"]]} 
            for m in st.session_state.messages if m["role"] != "system"
        ])
        
        return chat.send_message(user_text, stream=True)
        
    except Exception as e:
        # エラー内容を文字列として返す
        return f"エラーが発生しました: {str(e)}"

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
            
            # 回答生成
            response_stream = get_ai_response(prompt)
            
            # エラー判定（文字列が返ってきたらエラーとみなす）
            if isinstance(response_stream, str):
                # 404エラーなどの場合、ユーザーに見やすいメッセージを出す
                if "404" in response_stream:
                    st.error("⚠️ モデルが見つかりません。requirements.txt の google-generativeai のバージョンを確認してください。")
                    st.code(response_stream)
                elif "429" in response_stream:
                    st.error("⚠️ 使いすぎて制限がかかりました。数分待ってから試してください。")
                    st.code(response_stream)
                else:
                    st.error(response_stream)
            else:
                try:
                    for chunk in response_stream:
                        if chunk.text:
                            full_response += chunk.text
                            response_container.markdown(full_response + "▌")
                    response_container.markdown(full_response)
                    
                    st.session_state.messages.append({"role": "model", "content": full_response})
                    
                    st.session_state.study_log.append({
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "question": prompt,
                        "context": book_context,
                        "model": "gemini-1.5-flash"
                    })
                except Exception as e:
                    response_container.error(f"生成中にエラーが発生しました: {e}")

with tab2:
    st.header("📝 復習ノート")
    st.write("質問した履歴がここに蓄積されます。")
    
    if st.session_state.study_log:
        df = pd.DataFrame(st.session_state.study_log)
        st.dataframe(df, use_container_width=True)
        
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 学習ログをCSVでダウンロード",
            data=csv,
            file_name='my_study_log.csv',
            mime='text/csv',
        )
    else:
        st.info("まだ質問履歴がありません。チャットタブで質問してみましょう！")

