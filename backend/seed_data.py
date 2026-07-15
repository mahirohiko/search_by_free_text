import os
import warnings
import torch
import chromadb
from transformers import AutoTokenizer, AutoModel
import torch.nn.functional as F
import httpx

warnings.filterwarnings("ignore")
os.environ["CURL_CA_BUNDLE"] = ""
os.environ["REQUESTS_CA_BUNDLE"] = ""
original_client = httpx.Client
def patched_client(*args, **kwargs):
    kwargs["verify"] = False
    return original_client(*args, **kwargs)
httpx.Client = patched_client

device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
print(f"🚀 デバイス: {device} でモデルをロード中...")

model_name = "intfloat/multilingual-e5-small"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModel.from_pretrained(model_name).to(device)

def get_embedding(texts):
    encoded = tokenizer(texts, padding=True, truncation=True, max_length=128, return_tensors='pt').to(device)
    with torch.no_grad():
        model_output = model(**encoded)
    embeddings = model_output.last_hidden_state.mean(dim=1)
    embeddings = F.normalize(embeddings, p=2, dim=1)
    return embeddings.cpu().numpy().tolist()

# DBの初期化（古いデータを消して作り直す）
client = chromadb.PersistentClient(path="./ec_sandbox_kb")
try:
    client.delete_collection("ec_products")
except:
    pass
collection = client.create_collection(name="ec_products")

# ==========================================
# 💎 豪華版：EC商品カタログ（全20件）
# ==========================================
docs = [
    # アウター
    "秋口の肌寒い季節にぴったりな、薄手のマウンテンパーカー。撥水加工が施されており、ちょっとしたお出かけからアウトドアまで幅広く活躍します。",
    "極寒の冬キャンプや野外アクティビティに最適な、高保温性のプレミアムダウンジャケット。軽量ながらもしっかりと体温を逃がしません。",
    "春先の通勤に最適な、スプリングトレンチコート。シワになりにくい素材で、スーツの上からもスマートに羽織れます。",
    "バイクツーリングやロックなスタイルにハマる、本革のシングルライダースジャケット。着込むほどに体に馴染むエイジングが楽しめます。",
    "ちょっとコンビニに行く時など、ワンマイルウェアとして便利なふわふわのフリースジャケット。軽くて暖かく、洗濯機で丸洗い可能です。",
    
    # トップス
    "リモートワークのビデオ会議でも映える、シワになりにくいノーアイロンのオフィスカジュアルシャツ。ストレッチ素材で長時間のデスクワークも快適です。",
    "夏の海やプールに最適な、UVカット機能付きのリネン（麻）シャツ。通気性が抜群で、日焼け対策をしながら涼しく過ごせます。",
    "ストリートファッションに欠かせない、ヘビーウェイトのオーバーサイズパーカー。厚手のコットン生地でフードの立ち上がりが綺麗です。",
    "上品な光沢感が特徴の、シルク混ハイネックセーター。レストランでのディナーなど、少しフォーマルな場にも着ていける高級感があります。",
    "吸水速乾性に優れたスポーツ用Tシャツ。ジムでの筋トレや長時間のランニングでも、汗でベタつかずサラサラの着心地をキープします。",

    # ボトムス
    "どんなトップスにも合わせやすい、スリムフィットの黒スキニーパンツ。驚異のストレッチ性で、しゃがんでも全く窮屈感がありません。",
    "真冬のアウトドアに特化した、裏起毛の防寒カーゴパンツ。複数のポケットを備え、手ぶらで行動したいキャンパーに大人気です。",
    "結婚式の二次会やパーティーにも使える、センタープレスの入ったエレガントなスラックス。美脚効果が高く、ヒールとの相性も抜群です。",
    "リラックスした休日にぴったりな、ワイドシルエットのコーデュロイパンツ。温かみのある素材で、秋から冬にかけてヘビロテ確定です。",
    "フルマラソン対応の軽量ランニングショーツ。インナータイツ付きで股擦れを防ぎ、背面のジップポケットにはスマホや鍵を収納できます。",

    # シューズ
    "雨の日でも足元が濡れない完全防水スニーカー。滑りにくい特殊ソールを採用しており、梅雨の通勤・通学からフェスなどのイベントにもおすすめです。",
    "営業職のビジネスマンに捧ぐ、本革なのにスニーカーのように歩きやすい軽量ビジネスシューズ。長時間の外回りでも足が疲れません。",
    "厚底ソールでスタイルアップ効果のある、レトロデザインのダッドスニーカー。韓国ストリートファッションの定番アイテムです。",
    
    # ルームウェア＆小物
    "おうち時間を最高にリラックスして過ごせる、オーガニックコットン100%のルームウェア上下セット。肌触りが良く、そのまま寝巻きとしても使えます。",
    "夏の強い日差しから目を守る、偏光レンズ搭載のサングラス。ドライブ時のフロントガラスの反射や、釣りでの水面のギラつきを抑えます。"
]

metadatas = [
    {"category": "アウター", "price": 8900, "stock_status": "in_stock", "url": "https://ec-shop.example.com/items/out-01"},
    {"category": "アウター", "price": 28000, "stock_status": "in_stock", "url": "https://ec-shop.example.com/items/out-02"},
    {"category": "アウター", "price": 15000, "stock_status": "in_stock", "url": "https://ec-shop.example.com/items/out-03"},
    {"category": "アウター", "price": 45000, "stock_status": "out_of_stock", "url": "https://ec-shop.example.com/items/out-04"},
    {"category": "アウター", "price": 3900, "stock_status": "in_stock", "url": "https://ec-shop.example.com/items/out-05"},
    {"category": "トップス", "price": 4500, "stock_status": "in_stock", "url": "https://ec-shop.example.com/items/top-01"},
    {"category": "トップス", "price": 5500, "stock_status": "in_stock", "url": "https://ec-shop.example.com/items/top-02"},
    {"category": "トップス", "price": 6800, "stock_status": "out_of_stock", "url": "https://ec-shop.example.com/items/top-03"},
    {"category": "トップス", "price": 12000, "stock_status": "in_stock", "url": "https://ec-shop.example.com/items/top-04"},
    {"category": "トップス", "price": 2900, "stock_status": "in_stock", "url": "https://ec-shop.example.com/items/top-05"},
    {"category": "ボトムス", "price": 4900, "stock_status": "in_stock", "url": "https://ec-shop.example.com/items/bot-01"},
    {"category": "ボトムス", "price": 8500, "stock_status": "in_stock", "url": "https://ec-shop.example.com/items/bot-02"},
    {"category": "ボトムス", "price": 11000, "stock_status": "in_stock", "url": "https://ec-shop.example.com/items/bot-03"},
    {"category": "ボトムス", "price": 5900, "stock_status": "out_of_stock", "url": "https://ec-shop.example.com/items/bot-04"},
    {"category": "ボトムス", "price": 4500, "stock_status": "in_stock", "url": "https://ec-shop.example.com/items/bot-05"},
    {"category": "シューズ", "price": 6500, "stock_status": "in_stock", "url": "https://ec-shop.example.com/items/sho-01"},
    {"category": "シューズ", "price": 18000, "stock_status": "in_stock", "url": "https://ec-shop.example.com/items/sho-02"},
    {"category": "シューズ", "price": 9800, "stock_status": "in_stock", "url": "https://ec-shop.example.com/items/sho-03"},
    {"category": "ルームウェア", "price": 5000, "stock_status": "in_stock", "url": "https://ec-shop.example.com/items/rom-01"},
    {"category": "小物", "price": 3500, "stock_status": "in_stock", "url": "https://ec-shop.example.com/items/acc-01"}
]

ids = [f"item_{i:03d}" for i in range(1, 21)]

print("📥 ベクトル化を実行し、ChromaDBに書き込んでいます...")
embeddings = get_embedding(docs)
collection.add(
    embeddings=embeddings,
    documents=docs,
    metadatas=metadatas,
    ids=ids
)
print("✅ 豪華版モックデータ（全20件）の投入が完了しました！")