"use client"

import type React from "react"
import { useMemo, useState } from "react"
import {
  Search,
  SlidersHorizontal,
  Tag,
  Wallet,
  Link2,
  Sparkles,
  ShoppingCart,
  Loader2,
  PackageSearch,
  CircleCheck,
  CircleX,
} from "lucide-react"

// ---------------------------------------------------------------------------
// 型定義
// ---------------------------------------------------------------------------
type Category = "すべて" | "アウター" | "トップス" | "ボトムス" | "シューズ" | "ルームウェア" | "小物"

interface Product {
  id: string
  name: string
  category: Exclude<Category, "すべて">
  price: number
  description: string
  inStock: boolean
  url: string
  score: number // AIマッチ度 (%)
}

// 検索条件をまとめて外部APIへ送るためのペイロード型
interface SearchPayload {
  query: string
  category: Category
  maxPrice: number
  minScore: number
}

// ---------------------------------------------------------------------------
// カテゴリ一覧
// ---------------------------------------------------------------------------
const CATEGORIES: Category[] = ["すべて", "アウター", "トップス", "ボトムス", "シューズ", "ルームウェア", "小物"]

// ---------------------------------------------------------------------------
// モックデータ（APIが未接続でも画面を確認できるようにするためのサンプル）
// ---------------------------------------------------------------------------
const MOCK_PRODUCTS: Product[] = [
  {
    id: "p-001",
    name: "撥水スプリングコート",
    category: "アウター",
    price: 15000,
    description: "雨の日の通勤に最適な、撥水加工のスプリングコートです。春秋の肌寒い日にも活躍します。",
    inStock: true,
    url: "https://example-shop.jp/items/p-001",
    score: 85.3,
  },
  {
    id: "p-002",
    name: "軽量マウンテンパーカー",
    category: "アウター",
    price: 12800,
    description: "急な雨にも対応できる防水シェル。折り畳んで持ち運べる軽量設計で通勤・旅行に便利です。",
    inStock: true,
    url: "https://example-shop.jp/items/p-002",
    score: 78.1,
  },
  {
    id: "p-003",
    name: "オーガニックコットンTシャツ",
    category: "トップス",
    price: 3200,
    description: "肌触りの良いオーガニックコットン100%。一年を通して着回しやすい定番アイテムです。",
    inStock: true,
    url: "https://example-shop.jp/items/p-003",
    score: 64.7,
  },
  {
    id: "p-004",
    name: "ストレッチテーパードパンツ",
    category: "ボトムス",
    price: 8900,
    description: "動きやすいストレッチ素材。シワになりにくく、通勤にもオフにも使える万能パンツ。",
    inStock: false,
    url: "https://example-shop.jp/items/p-004",
    score: 71.9,
  },
  {
    id: "p-005",
    name: "防水レザースニーカー",
    category: "シューズ",
    price: 18500,
    description: "雨の日でも足元が濡れにくい防水レザー仕様。通勤スタイルに合わせやすいミニマルデザイン。",
    inStock: true,
    url: "https://example-shop.jp/items/p-005",
    score: 88.6,
  },
  {
    id: "p-006",
    name: "もこもこルームセットアップ",
    category: "ルームウェア",
    price: 5400,
    description: "秋冬に暖かいふわふわ素材。おうち時間を快適に過ごせる上下セットアップ。",
    inStock: true,
    url: "https://example-shop.jp/items/p-006",
    score: 42.3,
  },
  {
    id: "p-007",
    name: "折り畳み自動開閉傘",
    category: "小物",
    price: 2800,
    description: "ワンタッチ自動開閉。急な雨の日の通勤に忍ばせておきたいコンパクト傘です。",
    inStock: true,
    url: "https://example-shop.jp/items/p-007",
    score: 69.4,
  },
  {
    id: "p-008",
    name: "ウール混ニットカーディガン",
    category: "トップス",
    price: 9800,
    description: "春秋の羽織りに最適な軽量ニット。オンオフ問わず使える上品なデザイン。",
    inStock: false,
    url: "https://example-shop.jp/items/p-008",
    score: 55.2,
  },
]

// ---------------------------------------------------------------------------
// ユーティリティ：金額フォーマット
// ---------------------------------------------------------------------------
const formatYen = (value: number) => `¥${value.toLocaleString("ja-JP")}`

// マッチ度に応じたバッジの色
const scoreBadgeClass = (score: number) => {
  if (score >= 80) return "bg-emerald-100 text-emerald-700 ring-emerald-600/20"
  if (score >= 65) return "bg-amber-100 text-amber-700 ring-amber-600/20"
  return "bg-slate-100 text-slate-600 ring-slate-500/20"
}

// ---------------------------------------------------------------------------
// メインコンポーネント
// ---------------------------------------------------------------------------
export default function AiSearchPage() {
  // === データ連携用の State（この4つが検索条件として外部へ送られる） ===
  const [query, setQuery] = useState<string>("")
  const [category, setCategory] = useState<Category>("すべて")
  const [maxPrice, setMaxPrice] = useState<number>(50000)
  const [minScore, setMinScore] = useState<number>(50)

  // UI用の補助 State
  const [isLoading, setIsLoading] = useState<boolean>(false)
  const [results, setResults] = useState<Product[]>(MOCK_PRODUCTS)

  // -------------------------------------------------------------------------
  // 検索送信ハンドラ（仮関数）
  // 検索条件をコンソールに出力し、ローカルAPIへ fetch を投げる準備をしておく。
  // -------------------------------------------------------------------------
  // 💡 以下のコードに丸ごと差し替えてください
  const handleSearch = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    
    setIsLoading(true); 

    try {
      // 1. FastAPI (8001番ポート) にリクエストを送信！
      const response = await fetch("http://localhost:8001/api/search", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          query: query,       // 画面に入力された検索クエリ
          category: category, // 画面で選ばれたカテゴリ (例: "すべて")
          max_price: maxPrice, // 上限価格スライダーの値
          min_score: minScore  // AIマッチ度スライダーの値
        }),
      });

      if (!response.ok) {
        throw new Error("APIの呼び出しに失敗しました");
      }

      // 2. 返ってきたJSONデータを解析
      const data = await response.json();

      // 3. 画面に表示する商品リストをAPIの結果で更新！
      // バックエンドのレスポンス「results」を「setResults」に流し込みます
      setResults(data.results); 
      
    } catch (error) {
      console.error("検索エラー:", error);
      alert("検索中にエラーが発生しました。バックエンドのAPI（8001番ポート）が起動しているか確認してください。");
    } finally {
      setIsLoading(false);
    }
  };

  // -------------------------------------------------------------------------
  // フロント側フィルタリング（APIから返ってきたデータをそのまま表示するように変更）
  // -------------------------------------------------------------------------
  const filteredResults = useMemo(() => {
    // APIから返ってきた results をそのまま使います。
    // (検索ボタンを押していない初期状態の時は、MOCK_PRODUCTSがそのまま表示されます)
    return results;
  }, [results]);

  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-7xl px-4 py-8 md:px-6 lg:px-8">
        {/* ============================ ヘッダー ============================ */}
        <header className="mb-8">
          <h1 className="flex items-center gap-3 text-balance text-2xl font-bold tracking-tight text-slate-900 md:text-3xl">
            <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-indigo-600 text-white shadow-sm">
              <ShoppingCart className="h-6 w-6" aria-hidden="true" />
            </span>
            EC次世代AI検索エンジン
            <span className="rounded-full bg-indigo-100 px-2.5 py-1 text-xs font-semibold text-indigo-700">
              高精度版
            </span>
          </h1>
          <p className="mt-2 text-sm leading-relaxed text-slate-500">
            自然文であなたの要望を入力すると、AIが最適な商品をマッチ度順に提案します。
          </p>
        </header>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-[280px_1fr]">
          {/* ==================== 左サイドバー（フィルター） ==================== */}
          <aside className="lg:sticky lg:top-8 lg:h-fit">
            <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <h2 className="flex items-center gap-2 text-sm font-semibold text-slate-900">
                <SlidersHorizontal className="h-4 w-4 text-indigo-600" aria-hidden="true" />
                絞り込みフィルター
              </h2>

              {/* --- カテゴリ選択 --- */}
              <div className="mt-5">
                <label className="mb-2 block text-xs font-semibold uppercase tracking-wide text-slate-500">
                  カテゴリ
                </label>
                <div className="flex flex-wrap gap-2">
                  {CATEGORIES.map((c) => {
                    const active = category === c
                    return (
                      <button
                        key={c}
                        type="button"
                        onClick={() => setCategory(c)}
                        aria-pressed={active}
                        className={`rounded-full px-3 py-1.5 text-xs font-medium transition-colors ${
                          active
                            ? "bg-indigo-600 text-white shadow-sm"
                            : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                        }`}
                      >
                        {c}
                      </button>
                    )
                  })}
                </div>
              </div>

              {/* --- 上限価格スライダー --- */}
              <div className="mt-6">
                <div className="mb-2 flex items-center justify-between">
                  <label htmlFor="maxPrice" className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                    上限価格
                  </label>
                  <span className="text-sm font-bold text-indigo-600">{formatYen(maxPrice)}</span>
                </div>
                <input
                  id="maxPrice"
                  type="range"
                  min={1000}
                  max={50000}
                  step={1000}
                  value={maxPrice}
                  onChange={(e) => setMaxPrice(Number(e.target.value))}
                  className="h-2 w-full cursor-pointer appearance-none rounded-full bg-slate-200 accent-indigo-600"
                />
                <div className="mt-1 flex justify-between text-[11px] text-slate-400">
                  <span>¥1,000</span>
                  <span>¥50,000</span>
                </div>
              </div>

              {/* --- AIマッチ度（足切り閾値）スライダー --- */}
              <div className="mt-6">
                <div className="mb-2 flex items-center justify-between">
                  <label htmlFor="minScore" className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                    AIマッチ度（足切り）
                  </label>
                  <span className="text-sm font-bold text-indigo-600">{minScore}%</span>
                </div>
                <input
                  id="minScore"
                  type="range"
                  min={50}
                  max={100}
                  step={1}
                  value={minScore}
                  onChange={(e) => setMinScore(Number(e.target.value))}
                  className="h-2 w-full cursor-pointer appearance-none rounded-full bg-slate-200 accent-indigo-600"
                />
                <div className="mt-1 flex justify-between text-[11px] text-slate-400">
                  <span>50%</span>
                  <span>100%</span>
                </div>
              </div>

              <button
                type="button"
                onClick={() => handleSearch()}
                className="mt-6 flex w-full items-center justify-center gap-2 rounded-xl bg-slate-900 px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-slate-800"
              >
                <SlidersHorizontal className="h-4 w-4" aria-hidden="true" />
                この条件で絞り込む
              </button>
            </div>
          </aside>

          {/* ==================== メインコンテンツ ==================== */}
          <section>
            {/* --- 検索窓 --- */}
            <form
              onSubmit={handleSearch}
              className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
            >
              <label htmlFor="query" className="flex items-center gap-2 text-sm font-semibold text-slate-900">
                <Search className="h-4 w-4 text-indigo-600" aria-hidden="true" />
                どんな商品をお探しですか？
              </label>
              <div className="mt-3 flex flex-col gap-3 sm:flex-row">
                <div className="relative flex-1">
                  <Search
                    className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400"
                    aria-hidden="true"
                  />
                  <input
                    id="query"
                    type="text"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder="例：雨の日の通勤に使いたい、春秋に着れるもの"
                    className="w-full rounded-xl border border-slate-200 bg-slate-50 py-3 pl-10 pr-3 text-sm text-slate-900 outline-none transition-colors placeholder:text-slate-400 focus:border-indigo-500 focus:bg-white focus:ring-2 focus:ring-indigo-500/20"
                  />
                </div>
                <button
                  type="submit"
                  disabled={isLoading}
                  className="flex items-center justify-center gap-2 rounded-xl bg-indigo-600 px-6 py-3 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {isLoading ? (
                    <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                  ) : (
                    <Sparkles className="h-4 w-4" aria-hidden="true" />
                  )}
                  {isLoading ? "検索中..." : "AI検索"}
                </button>
              </div>
            </form>

            {/* --- 結果件数 --- */}
            <div className="mt-6 mb-3 flex items-center justify-between">
              <p className="text-sm text-slate-500">
                <span className="font-bold text-slate-900">{filteredResults.length}</span> 件の商品が見つかりました
              </p>
              <p className="text-xs text-slate-400">マッチ度の高い順に表示</p>
            </div>

            {/* --- 検索結果カードリスト --- */}
            {filteredResults.length === 0 ? (
              <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-slate-300 bg-white py-16 text-center">
                <PackageSearch className="h-10 w-10 text-slate-300" aria-hidden="true" />
                <p className="mt-3 text-sm font-medium text-slate-600">条件に一致する商品が見つかりませんでした</p>
                <p className="mt-1 text-xs text-slate-400">フィルターやマッチ度の閾値を調整してみてください。</p>
              </div>
            ) : (
              <ul className="flex flex-col gap-4">
                {filteredResults.map((product) => (
                  <li
                    key={product.id}
                    className="group rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition-shadow hover:shadow-md"
                  >
                    <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                      <div className="min-w-0 flex-1">
                        {/* マッチ度 & カテゴリ */}
                        <div className="flex flex-wrap items-center gap-2">
                          <span
                            className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-bold ring-1 ring-inset ${scoreBadgeClass(
                              product.score,
                            )}`}
                          >
                            <Sparkles className="h-3 w-3" aria-hidden="true" />
                            マッチ度: {product.score.toFixed(1)}%
                          </span>
                          <span className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600">
                            <Tag className="h-3 w-3" aria-hidden="true" />
                            {product.category}
                          </span>
                        </div>

                        {/* 商品名 */}
                        <h3 className="mt-3 text-base font-semibold text-slate-900">{product.name}</h3>

                        {/* 商品説明 */}
                        <p className="mt-1 text-sm leading-relaxed text-slate-500">{product.description}</p>

                        {/* URL */}
                        <a
                          href={product.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="mt-3 inline-flex max-w-full items-center gap-1.5 text-xs font-medium text-indigo-600 hover:underline"
                        >
                          <Link2 className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
                          <span className="truncate">{product.url}</span>
                        </a>
                      </div>

                      {/* 価格 & 在庫 */}
                      <div className="flex shrink-0 flex-row items-center justify-between gap-4 border-t border-slate-100 pt-3 sm:flex-col sm:items-end sm:border-t-0 sm:pt-0">
                        <div className="flex items-center gap-1.5 text-lg font-bold text-slate-900">
                          <Wallet className="h-4 w-4 text-slate-400" aria-hidden="true" />
                          {formatYen(product.price)}
                        </div>
                        {product.inStock ? (
                          <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-700">
                            <CircleCheck className="h-3.5 w-3.5" aria-hidden="true" />
                            在庫あり
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 rounded-full bg-rose-50 px-2.5 py-1 text-xs font-semibold text-rose-600">
                            <CircleX className="h-3.5 w-3.5" aria-hidden="true" />
                            在庫なし
                          </span>
                        )}
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>
      </div>
    </main>
  )
}
