import streamlit as st
import chromadb
import torch
from transformers import AutoTokenizer, AutoModel
import torch.nn.functional as F
import os
import warnings
import httpx

# # ==========================================
# # 👿 セキュリティソフト貫通パッチ
# # ==========================================
# warnings.filterwarnings("ignore")
# os.environ["CURL_CA_BUNDLE"] = ""
# os.environ["REQUESTS_CA_BUNDLE"] = ""
# original_client = httpx.Client
# def patched_client(*args, **kwargs):
#     kwargs["verify"] = False
#     return original_client(*args, **kwargs)
# httpx.Client = patched_client

# st.set_page_config(page_title="EC次世代AI検索 PoC", layout="wide")
# st.title("🛒 EC次世代AI検索エンジン (高精度版)")

# ==========================================
# 🧠 1. モデルのキャッシュロード
# ==========================================
@st.cache_resource
def load_ai_model():
    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    model_name = "intfloat/multilingual-e5-small"
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModel.from_pretrained(model_name).to(device)
    return tokenizer, model, device

tokenizer, model, device = load_ai_model()

# 💡 改善点2: Attention Maskを考慮したPooling処理
def average_pool(last_hidden_states, attention_mask):
    # パディング（無効な余白トークン）部分を0で埋めて計算から除外する
    last_hidden = last_hidden_states.masked_fill(~attention_mask[..., None].bool(), 0.0)
    return last_hidden.sum(dim=1) / attention_mask.sum(dim=1)[..., None]

def get_embedding(texts):
    encoded = tokenizer(texts, padding=True, truncation=True, max_length=128, return_tensors='pt').to(device)
    with torch.no_grad():
        model_output = model(**encoded)
    
    # 💡 単純平均ではなく、Attention Maskを使った高精度な平均化
    embeddings = average_pool(model_output.last_hidden_state, encoded['attention_mask'])
    embeddings = F.normalize(embeddings, p=2, dim=1)
    return embeddings.cpu().numpy().tolist()

# ==========================================
# 🗄️ 2. DB接続
# ==========================================
@st.cache_resource
def load_db():
    client = chromadb.PersistentClient(path="./ec_sandbox_kb")
    return client.get_collection(name="ec_products")

collection = load_db()

# ==========================================
# 🎛️ 3. UIと検索ロジック
# ==========================================
st.sidebar.header("🔍 絞り込みフィルター")
selected_category = st.sidebar.selectbox("カテゴリ", ["すべて", "アウター", "トップス", "ボトムス", "シューズ", "ルームウェア", "小物"])
max_price = st.sidebar.slider("上限価格", 1000, 50000, 50000, step=1000)

# 💡 精度が向上したため、足切り閾値のデフォルトを高め（75%）に設定
min_score = st.sidebar.slider("AIマッチ度（足切り閾値）", 50, 100, 75)

query = st.text_input("🔎 どんな商品をお探しですか？", placeholder="例：雨の日の通勤に使いたい、春秋に着れるもの")

if query:
    # 💡 改善点1: クエリに 'query: ' プレフィックスを付与してベクトル化
    e5_query = f"query: {query}"
    query_embedding = get_embedding([e5_query])
    
    where_clause = {"price": {"$lte": max_price}}
    if selected_category != "すべて":
        where_clause = {
            "$and": [
                {"price": {"$lte": max_price}},
                {"category": selected_category}
            ]
        }

    # 内部的に多めに5件取得し、スコアの足切りで厳選する
    results = collection.query(
        query_embeddings=query_embedding,
        n_results=5,
        where=where_clause 
    )

    st.markdown("### 🎯 検索結果")
    
    hit_count = 0
    for i in range(len(results['documents'][0])):
        doc = results['documents'][0][i]
        meta = results['metadatas'][0][i]
        distance = results['distances'][0][i]
        score = max(0, (1.0 - distance)) * 100
        
        # 足切り処理
        if score < min_score:
            continue
            
        hit_count += 1
        
        with st.expander(f"【マッチ度: {score:.1f}%】 🏷️ {meta['category']} / 💰 ¥{meta['price']:,}", expanded=True):
            st.write(f"**商品説明:** {doc}")
            status = "🟢 在庫あり" if meta['stock_status'] == 'in_stock' else "🔴 在庫なし"
            st.caption(f"🔗 {meta['url']} | 📦 {status}")

    if hit_count == 0:
        st.warning("条件に一致する商品が見つかりませんでした。マッチ度の閾値を下げるか、上限価格を上げてください。")