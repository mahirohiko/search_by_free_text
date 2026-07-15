from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import chromadb
import torch
from transformers import AutoTokenizer, AutoModel
import torch.nn.functional as F
import os
import warnings
import httpx

# # ==========================================
# # 👿 セキュリティソフト貫通パッチ (そのまま流用)
# # ==========================================
# warnings.filterwarnings("ignore")
# os.environ["CURL_CA_BUNDLE"] = ""
# os.environ["REQUESTS_CA_BUNDLE"] = ""
# original_client = httpx.Client
# def patched_client(*args, **kwargs):
#     kwargs["verify"] = False
#     return original_client(*args, **kwargs)
# httpx.Client = patched_client

# ==========================================
# 🏗️ FastAPIアプリケーションとCORS設定
# ==========================================
app = FastAPI(title="EC次世代AI検索 API")

# Next.js (通常 localhost:3000) からの通信を許可する設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 本番環境では ["http://localhost:3000"] などに絞ります
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# 📦 データの入出力定義 (Pydantic Models)
# ==========================================
class SearchRequest(BaseModel):
    query: str
    category: str = "すべて"
    max_price: int = 50000
    min_score: float = 75.0

class SearchResult(BaseModel):
    score: float
    category: str
    price: int
    description: str
    stock_status: str
    url: str

class SearchResponse(BaseModel):
    results: List[SearchResult]
    hit_count: int

# ==========================================
# 🧠 AIモデルとDBのロード (グローバルスコープ)
# ==========================================
device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
model_name = "intfloat/multilingual-e5-small"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModel.from_pretrained(model_name).to(device)

client = chromadb.PersistentClient(path="./ec_sandbox_kb")
collection = client.get_collection(name="ec_products")

# ==========================================
# ⚙️ コアロジック (そのまま流用)
# ==========================================
def average_pool(last_hidden_states, attention_mask):
    last_hidden = last_hidden_states.masked_fill(~attention_mask[..., None].bool(), 0.0)
    return last_hidden.sum(dim=1) / attention_mask.sum(dim=1)[..., None]

def get_embedding(texts):
    encoded = tokenizer(texts, padding=True, truncation=True, max_length=128, return_tensors='pt').to(device)
    with torch.no_grad():
        model_output = model(**encoded)
    
    embeddings = average_pool(model_output.last_hidden_state, encoded['attention_mask'])
    embeddings = F.normalize(embeddings, p=2, dim=1)
    return embeddings.cpu().numpy().tolist()

# ==========================================
# 🚀 APIエンドポイント
# ==========================================
@app.post("/api/search", response_model=SearchResponse)
def search_products(request: SearchRequest):
    if not request.query.strip():
        return SearchResponse(results=[], hit_count=0)

    # クエリにプレフィックスを付与してベクトル化
    e5_query = f"query: {request.query}"
    query_embedding = get_embedding([e5_query])
    
    # 検索条件の組み立て
    where_clause = {"price": {"$lte": request.max_price}}
    if request.category != "すべて":
        where_clause = {
            "$and": [
                {"price": {"$lte": request.max_price}},
                {"category": request.category}
            ]
        }

    # DB検索
    db_results = collection.query(
        query_embeddings=query_embedding,
        n_results=5,
        where=where_clause 
    )

    final_results = []
    
    # 結果が空の場合のハンドリング
    if not db_results['documents'] or not db_results['documents'][0]:
        return SearchResponse(results=[], hit_count=0)

    # 結果のパースと足切り
    for i in range(len(db_results['documents'][0])):
        doc = db_results['documents'][0][i]
        meta = db_results['metadatas'][0][i]
        distance = db_results['distances'][0][i]
        score = max(0, (1.0 - distance)) * 100
        
        # 足切り処理
        if score < request.min_score:
            continue
            
        final_results.append(
            SearchResult(
                score=round(score, 1),
                category=meta.get('category', 'Unknown'),
                price=meta.get('price', 0),
                description=doc,
                stock_status=meta.get('stock_status', 'Unknown'),
                url=meta.get('url', '#')
            )
        )

    return SearchResponse(results=final_results, hit_count=len(final_results))