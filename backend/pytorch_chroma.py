import os
import warnings
import torch
import chromadb
from transformers import AutoTokenizer, AutoModel
import torch.nn.functional as F
import httpx

# 👿 セキュリティソフト貫通パッチ（前回と同じ）
warnings.filterwarnings("ignore")
os.environ["CURL_CA_BUNDLE"] = ""
os.environ["REQUESTS_CA_BUNDLE"] = ""
original_client = httpx.Client
def patched_client(*args, **kwargs):
    kwargs["verify"] = False
    return original_client(*args, **kwargs)
httpx.Client = patched_client

# ==========================================
# 1. 🧠 PyTorch モデルの準備 (MPS有効化)
# ==========================================
device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
model_name = "intfloat/multilingual-e5-small"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModel.from_pretrained(model_name).to(device)

def get_embedding(texts):
    encoded = tokenizer(texts, padding=True, truncation=True, max_length=128, return_tensors='pt').to(device)
    with torch.no_grad():
        model_output = model(**encoded)
    embeddings = model_output.last_hidden_state.mean(dim=1)
    embeddings = F.normalize(embeddings, p=2, dim=1)
    # 💡 ChromaDBに渡すために、PyTorchのTensorを通常のPythonリストに変換
    return embeddings.cpu().numpy().tolist()

# ==========================================
# 2. 🗄️ ChromaDB のセットアップ（ディスクに保存）
# ==========================================
# カレントディレクトリに "company_kb" というフォルダを作ってデータを永続化
client = chromadb.PersistentClient(path="./company_kb")

# "notion_slack_docs" という名前のコレクション（テーブルのようなもの）を作成
# 既に存在する場合は取得する
collection = client.get_or_create_collection(name="notion_slack_docs")

# ==========================================
# 3. 📝 データの保存（インデックス作成）※初回バッチ処理のイメージ
# ==========================================
# まだデータが入っていなければ登録する
if collection.count() == 0:
    print("📥 データベースが空のため、初期データを投入します...")
    
    docs = [
        "経費精算は月末までにシステムXで申請してください。",
        "リモートワーク時の通信費補助は毎月5000円です。",
        "サーバーの再起動手順はWikiのインフラページに記載されています。"
    ]
    
    # メタデータ（ここがChromaの最強の強み！URLやソース元を自由に付与できる）
    metadatas = [
        {"source": "notion", "url": "https://notion.so/expense", "author": "総務部"},
        {"source": "slack", "url": "https://slack.com/.../123", "author": "人事部"},
        {"source": "notion", "url": "https://notion.so/server", "author": "SREチーム"}
    ]
    
    # ID（一意の文字列）
    ids = ["doc_1", "doc_2", "doc_3"]
    
    # PyTorchでベクトル化
    embeddings = get_embedding(docs)
    
    # Chromaに一撃で保存！
    collection.add(
        embeddings=embeddings,
        documents=docs,
        metadatas=metadatas,
        ids=ids
    )
    print("✅ データの保存が完了しました！")

# ==========================================
# 4. 🔍 検索の実行
# ==========================================
print(f"📊 現在のドキュメント総数: {collection.count()}件")

query = "ネット代の補助って出るんだっけ？"
print(f"\n🔍 検索クエリ: 「{query}」")

# クエリをベクトル化してChromaに投げる
query_embedding = get_embedding([query])

# n_results で上位何件を取得するか指定
results = collection.query(
    query_embeddings=query_embedding,
    n_results=2
)

# 結果の表示
print("=" * 50)
for i in range(len(results['documents'][0])):
    doc = results['documents'][0][i]
    meta = results['metadatas'][0][i]
    # Chromaは距離(Distance)を返すため、値が小さいほど似ている（0に近いほど完全一致）
    distance = results['distances'][0][i]
    
    print(f"類似度: {(1 - distance):.3f} | ソース: {meta['source'].upper()}")
    print(f"本文: {doc}")
    print(f"URL: {meta['url']}")
    print("-" * 50)