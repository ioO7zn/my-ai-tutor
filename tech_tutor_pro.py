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

# --- 2. デザイン調整 (シンプルかつ確実に見やすく) ---
st.markdown("""
<style>
    /* 全体の背景と文字色 */
    .stApp {
        background-color: #f8f9fa;
        color: #333333;
    }
    
    /* ユーザーのチャット背景（白） */
    .stChatMessage[data-testid="stChatMessage"]:nth-child(odd) {
        background-color: white;
        border-radius: 12px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        padding: 1rem;
    }
    
    /* AIのチャット背景（薄い青） */
    .stChatMessage[data-testid="stChatMessage"]:nth-child(even) {
        background-color: #f0f7ff;
        border-radius: 12px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        padding: 1rem;
    }

    /* 文字色を黒に固定（ダークモード対策） */
    p, div, li, h1, h2, h3, h4, h5, h6 {
        color: #333333 !important;
    }
    
    /* コードブロックは見やすく */
    code {
        color: #d63384 !important;
        font-family: 'Consolas', 'Monaco', monospace;
    }
    
    /* Expander（アコーディオン）のデザイン */
    .streamlit-expanderHeader {
        background-color: #ffffff;
        border: 1px solid #ddd;
        border-radius: 8px;
    }
    .streamlit-expanderContent {
        background-color: #ffffff;
        border: 1px solid #ddd;
        border-top: none;
        border-radius: 0 0 8px 8px;
    }
</style>
""", unsafe_allow_html=True)

# --- 3. セッション管理 ---
if "messages" not in st.session_state:
    st.session_state.messages = []
    # 最初のメッセージ
    st.session_state.messages.append({
        "role": "assistant",
        "content": "こんにちは！一緒に楽しく勉強しましょう。何について知りたいですか？"
    })

if "study_log" not in st.session_state:
    st.session_state.study_log = []

# --- 4. AIロジック関数 ---
def get_ai_response(user_text, api_key, context, level):
    try:
        genai.configure(api_key=api_key)
        
        # 自然な流れを作るためのプロンプト
        system_prompt = f"""
        あなたは『{context}』を教える、親しみやすいメンターです。
        相手のレベルは『{level}』です。
        
        【指示】
        1. ユーザーの質問に対し、**比喩（たとえ話）**を使って分かりやすく解説してください。
        2. 解説の後に、「では、理解度チェックです！」という流れで、**3択クイズの問題文**を出してください。
        3. ここまでは普通に出力し、**正解と解説だけ**を隠します。
        4. 正解と解説を書く前に、必ず区切り文字 `///HIDDEN///` を入れてください。
        
        【出力イメージ】
        （解説文章）
        （コード例など）
        （クイズの問題文）
        
        ///HIDDEN///
        
        （クイズの正解）
        （なぜそうなるかの解説）
        """
        
        model = genai.GenerativeModel('models/gemini-flash-latest', system_instruction=system_prompt)
        
        # 履歴の整形（エラー防止のため単純化）
        history_api = []
        for m in st.session_state.messages:
            role = "user" if m["role"] == "user" else "model"
            # 過去の区切り文字は見えないように置換して履歴に入れる
            clean_text = m["content"].replace("///HIDDEN///", "\n\n【正解】\n")
            history_api.append({"role": role, "parts": [clean_text]})

        chat = model.start_chat(history=history_api)
        response = chat.send_message(user_text)
        return response.text
        
    except Exception as e:
        return f"エラー: {str(e)}"

# メッセージ表示用関数
def render_message(role, text):
    with st.chat_message(role, avatar="🧑‍💻" if role == "user" else "🤖"):
        # AIの場合、区切り文字で分割して表示
        if role == "assistant" and "///HIDDEN///" in text:
            parts = text.split("///HIDDEN///")
            main_content = parts[0]
            hidden_content = parts[1] if len(parts) > 1 else ""
            
            st.markdown(main_content)
            
            if hidden_content:
                with st.expander("👀 クリックして正解を見る"):
                    st.markdown(hidden_content)
        else:
            # ユーザーまたは区切り文字がない場合
            st.markdown(text)

# --- 5. アプリの構成 ---

# サイドバー
with st.sidebar:
    st.header("⚙️ 学習設定")
    if "GOOGLE_API_KEY" in st.secrets:
        api_key = st.secrets["GOOGLE_API_KEY"]
    else:
        api_key = st.text_input("Google API Key", type="password")
    
    st.divider()
    book_context = st.text_input("📚 テーマ", value="Python基礎")
    user_level = st.select_slider("📊 レベル", options=["超初心者", "初心者", "中級者"], value="初心者")
    
    st.divider()
    # 経験値バー
    q_count = sum(1 for m in st.session_state.messages if m["role"] == "user")
    st.write(f"🔥 今日の学習: {q_count}問")
    st.progress(min(q_count / 10, 1.0))
    
    st.divider()
    if st.button("🗑️ 会話をリセット"):
        st.session_state.messages = []
        st.session_state.messages.append({"role": "assistant", "content": "リセットしました！また新しい質問をどうぞ。"})
        st.rerun()

# メインエリア
st.title("🎓 Tech Tutor AI")
tab1, tab2 = st.tabs(["💬 チャット学習", "📝 復習ノート"])

# === タブ1: チャット ===
with tab1:
    # 履歴表示
    for msg in st.session_state.messages:
        render_message(msg["role"], msg["content"])
    
    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

    # 次のアクション提案（AIの直後のみ）
    if st.session_state.messages and st.session_state.messages[-1]["role"] == "assistant":
        st.caption("💡 気になるボタンを押して深掘りしよう")
        col1, col2, col3 = st.columns(3)
        next_prompt = None
        if col1.button("もっと詳しく解説"):
            next_prompt = "今の説明、ちょっと難しかったです。もっと簡単な言葉で詳しく教えて！"
        if col2.button("実践コード例"):
            next_prompt = "それを使った、実務でよくあるコード例を見せてください。"
        if col3.button("注意点は？"):
            next_prompt = "それを使う時に、初心者がやりがちな失敗はありますか？"
            
        if next_prompt:
            # ボタンが押されたら即実行処理へ（下のif文へ渡す）
            st.session_state["temp_input"] = next_prompt
            st.rerun()

    # 入力処理
    # ボタン入力(temp_input)があるか、チャット入力(chat_input)があるか
    user_input = st.chat_input("質問を入力してください...")
    if "temp_input" in st.session_state and st.session_state["temp_input"]:
        user_input = st.session_state["temp_input"]
        del st.session_state["temp_input"] # 使い終わったら消す

    if user_input:
        if not api_key:
            st.warning("⚠️ サイドバーでAPIキーを設定してください")
            st.stop()
            
        # 1. ユーザーメッセージ追加
        st.session_state.messages.append({"role": "user", "content": user_input})
        
        # 2. 画面更新してユーザーメッセージを表示させる
        # （Streamlitの仕様上、ここでrerunするとスムーズ）
        st.rerun()

# メッセージ生成処理（rerun後に最新がユーザーの場合に実行）
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    last_user_msg = st.session_state.messages[-1]["content"]
    
    with tab1:
        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("AIが回答を作成中..."):
                response_text = get_ai_response(last_user_msg, api_key, book_context, user_level)
                
                # 画面表示
                parts = response_text.split("///HIDDEN///")
                st.markdown(parts[0])
                if len(parts) > 1:
                    with st.expander("👀 クリックして正解を見る"):
                        st.markdown(parts[1])
                
                # 履歴保存
                st.session_state.messages.append({"role": "assistant", "content": response_text})
                
                # ログ保存
                explanation = parts[0]
                answer = parts[1] if len(parts) > 1 else "（解説のみ）"
                st.session_state.study_log.append({
                    "time": datetime.now().strftime("%H:%M"),
                    "q": last_user_msg,
                    "a_main": explanation,
                    "a_hidden": answer
                })
                
                # 完了したら再描画してボタンを表示
                st.rerun()

# === タブ2: 復習ノート ===
with tab2:
    st.info("質問した内容がカード形式で保存されます。")
    if st.session_state.study_log:
        for log in reversed(st.session_state.study_log):
            with st.expander(f"Q. {log['q']} ({log['time']})"):
                st.markdown("**【解説と問題】**")
                st.markdown(log['a_main'])
                if log['a_hidden'] != "（解説のみ）":
                    st.divider()
                    st.markdown("**【正解】**")
                    st.markdown(log['a_hidden'])
    else:
        st.write("まだ履歴がありません。")

