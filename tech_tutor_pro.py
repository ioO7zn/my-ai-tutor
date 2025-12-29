
import streamlit as st
import google.generativeai as genai
import pandas as pd
from datetime import datetime
import re # 正規表現を使うためにインポート

# --- 1. ページ設定とデザイン（徹底的に見やすく） ---
st.set_page_config(
    page_title="Tech Tutor AI",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 見やすさ特化のCSS
st.markdown("""
<style>
    /* アプリ全体の背景と文字色を強制指定 */
    .stApp {
        background-color: #f4f6f9; /* 薄いグレーの背景 */
        color: #333333;
    }

    /* ----------------------------------
       チャット吹き出しのスタイル
    ---------------------------------- */
    /* ユーザーとAIのメッセージ共通設定 */
    div[data-testid="stChatMessage"] {
        background-color: transparent !important;
        padding: 0px !important;
    }

    /* メッセージの中身（カード部分） */
    .chat-card {
        padding: 20px;
        border-radius: 12px;
        margin-bottom: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        line-height: 1.6; /* 行間を広げて読みやすく */
        font-size: 16px; /* 文字サイズを少し大きく */
    }

    /* ユーザーの吹き出し */
    .user-card {
        background-color: #ffffff;
        border-left: 6px solid #2ecc71; /* 緑 */
        color: #111111 !important;
    }

    /* AIの吹き出し */
    .ai-card {
        background-color: #ffffff;
        border-left: 6px solid #3498db; /* 青 */
        color: #111111 !important;
    }

    /* ----------------------------------
       復習ノート（Expander）のスタイル
    ---------------------------------- */
    /* Expanderのヘッダー（クリックする部分） */
    .streamlit-expanderHeader {
        background-color: #ffffff !important;
        color: #111111 !important;
        border-radius: 8px !important;
        font-weight: bold;
        border: 1px solid #ddd;
    }
    
    /* Expanderの中身 */
    .streamlit-expanderContent {
        background-color: #ffffff !important;
        color: #111111 !important;
        border: 1px solid #ddd;
        border-top: none;
        padding: 20px !important;
    }

    /* コードブロックの調整 */
    code {
        color: #d63384 !important;
        font-weight: bold;
    }
    .stCodeBlock {
        background-color: #2b2b2b !important;
    }

    /* ボタンのデザイン */
    .stButton button {
        border-radius: 20px;
        font-weight: bold;
        background-color: #ffffff;
        border: 1px solid #ccc;
        color: #333;
        transition: all 0.3s;
    }
    .stButton button:hover {
        border-color: #3498db;
        color: #3498db;
        background-color: #f0f8ff;
    }

    /* 強制的に黒文字にするクラス（Markdown用） */
    .black-text {
        color: #000000 !important;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. セッション情報の初期化 ---
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.messages.append({
        "role": "assistant", 
        "content": "こんにちは！一緒に勉強しましょう。\n何について知りたいですか？"
    })

if "study_log" not in st.session_state:
    st.session_state.study_log = []

# --- 3. ロジック関数（賢い分割表示機能付き） ---
def get_ai_response(user_text, api_key, book_context, user_level):
    try:
        genai.configure(api_key=api_key)
        
        # AIに「区切り文字」を使わせて、後でプログラムで分解できるようにする
        system_prompt = f"""
        あなたは『{book_context}』を教えるプロのメンターです。相手は『{user_level}』です。
        
        【重要：出力フォーマット】
        以下の3つのセクションを「###」で区切って出力してください。
        
        セクション1: 解説
        （ここに比喩を使った分かりやすい解説とコード例を書く）
        
        ###
        
        セクション2: クイズ問題
        （ここに3択クイズの問題文だけを書く。答えは書かない）
        
        ###
        
        セクション3: クイズの答えと解説
        （ここに正解と、なぜそうなるかの解説を書く）
        
        【ルール】
        - 専門用語は必ず日常の例え話を入れる。
        - 口調は優しく、絵文字を使う。
        - 最後のセクション3は、ユーザーがクリックするまで見えないようにするため、必ず区切ること。
        """
        
        model = genai.GenerativeModel('models/gemini-flash-latest', system_instruction=system_prompt)
        
        # 履歴の変換
        history_for_api = []
        for m in st.session_state.messages:
            role = "user" if m["role"] == "user" else "model"
            # 過去のメッセージから区切り文字を除去して履歴に入れる（混乱防止）
            clean_content = m["content"].replace("###", "\n") 
            history_for_api.append({"role": role, "parts": [clean_content]})

        chat = model.start_chat(history=history_for_api)
        response = chat.send_message(user_text)
        return response.text
        
    except Exception as e:
        return f"エラー: {str(e)}"

# メッセージを表示する関数（解説とクイズを分離する機能）
def display_formatted_message(content, role):
    if role == "user":
        st.markdown(f'<div class="chat-card user-card">{content}</div>', unsafe_allow_html=True)
    else:
        # AIの回答の場合、###で区切られているかチェック
        parts = content.split("###")
        
        # カード開始
        st.markdown('<div class="chat-card ai-card">', unsafe_allow_html=True)
        
        # パート1: 解説
        if len(parts) >= 1:
            st.markdown(parts[0].strip())
        
        # パート2: クイズ問題（もしあれば）
        if len(parts) >= 2:
            st.divider()
            st.markdown("##### 🧠 理解度クイズ")
            st.markdown(parts[1].strip())
            
        # パート3: 答え（Expanderに隠す）
        if len(parts) >= 3:
            with st.expander("👀 答えと解説を見る"):
                st.markdown(parts[2].strip())
        
        # カード終了
        st.markdown('</div>', unsafe_allow_html=True)

# --- 4. サイドバー（設定） ---
with st.sidebar:
    st.title("⚙️ 設定")
    
    if "GOOGLE_API_KEY" in st.secrets:
        api_key = st.secrets["GOOGLE_API_KEY"]
    else:
        api_key = st.text_input("Google API Key", type="password")
        if not api_key:
            st.warning("⚠️ APIキーを入れてください")
    
    st.markdown("---")
    book_context = st.text_input("📚 学習テーマ", value="Python基礎")
    user_level = st.select_slider("📊 レベル", options=["超初心者", "初心者", "中級者"], value="初心者")
    
    st.markdown("---")
    # 学習ゲージ
    q_count = len([m for m in st.session_state.messages if m["role"] == "user"])
    st.write(f"🔥 経験値: Lv.{q_count}")
    st.progress(min(q_count / 20, 1.0))

    st.markdown("---")
    if st.button("🗑️ 会話クリア", use_container_width=True):
        st.session_state.messages = []
        st.session_state.messages.append({"role": "assistant", "content": "リセットしました！何を学びますか？"})
        st.rerun()

# --- 5. メイン画面 ---
st.title("🎓 Tech Tutor AI")

# タブ表示
tab1, tab2 = st.tabs(["💬 チャット", "📝 復習ノート"])

# === チャットタブ ===
with tab1:
    # 履歴の表示
    for msg in st.session_state.messages:
        display_formatted_message(msg["content"], msg["role"])

    st.markdown("<br>", unsafe_allow_html=True) # 余白

    # AIからの提案（直近がAIの場合）
    suggested_text = None
    if st.session_state.messages and st.session_state.messages[-1]["role"] == "assistant":
        st.info("💡 次はこんなことを聞いてみませんか？")
        col_s1, col_s2, col_s3 = st.columns(3)
        if col_s1.button("もっと詳しく", key="btn_detail"):
            suggested_text = "もう少し詳しく、別の例えで教えて"
        if col_s2.button("コード例が見たい", key="btn_code"):
            suggested_text = "実践的なコード例を書いて"
        if col_s3.button("間違いやすい点は？", key="btn_warn"):
            suggested_text = "初心者がやりがちなミスは？"

    # 入力エリア（画面下部）
    prompt = st.chat_input("質問を入力...")

    # 入力決定ロジック
    final_input = prompt if prompt else suggested_text

    if final_input:
        if not api_key:
            st.error("APIキーが必要です")
            st.stop()

        # ユーザー入力を保存・表示
        st.session_state.messages.append({"role": "user", "content": final_input})
        display_formatted_message(final_input, "user")

        # AI処理中...
        with st.spinner("AIが考え中...✍️"):
            response_text = get_ai_response(final_input, api_key, book_context, user_level)
        
        # AI回答を保存・表示
        st.session_state.messages.append({"role": "assistant", "content": response_text})
        
        # ログにも保存（クイズ形式に対応して保存）
        # parts[0]=解説, parts[1]=問題, parts[2]=答え
        parts = response_text.split("###")
        question_part = final_input
        answer_part = parts[0]
        quiz_part = parts[1] if len(parts) > 1 else ""
        quiz_ans_part = parts[2] if len(parts) > 2 else ""

        st.session_state.study_log.append({
            "timestamp": datetime.now().strftime("%m/%d %H:%M"),
            "question": question_part,
            "explanation": answer_part,
            "quiz_q": quiz_part,
            "quiz_a": quiz_ans_part
        })
        
        st.rerun() # 画面を更新してきれいに表示

# === 復習ノートタブ ===
with tab2:
    st.header("📝 復習カード")
    st.caption("クリックすると詳細が開きます。")

    if st.session_state.study_log:
        for log in reversed(st.session_state.study_log):
            # カードのタイトル（質問内容）
            with st.expander(f"Q. {log['question']} ({log['timestamp']})"):
                # 解説エリア
                st.markdown("**【解説】**")
                st.markdown(log['explanation'])
                
                # クイズがあった場合のみ表示
                if log['quiz_q']:
                    st.divider()
                    st.markdown("**【クイズ】**")
                    st.markdown(log['quiz_q'])
                    # 答えはさらにネスト（入れ子）したExpanderに入れるか、詳細エリアの下部に配置
                    st.info(f"**答え:** {log['quiz_a']}")
    else:
        st.info("まだ履歴がありません。")
        
    # CSVダウンロード
    if st.session_state.study_log:
        df = pd.DataFrame(st.session_state.study_log)
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 ログを保存", csv, "study_log.csv", "text/csv")
