import { useQuery } from "@tanstack/react-query"
import { api } from "@/lib/api"
import GroceryItem, { type GroceryItemData } from "@/components/groceryitem"
import { Button } from "@/components/ui/button"
import { MOCK_RESPONSE } from "@/lib/mockGroceryList"

const USE_MOCK = import.meta.env.VITE_USE_MOCK === "true"

interface GroceryListProps {
  profile: Record<string, unknown>
}

interface RecommendationsResponse {
  items: GroceryItemData[]
  estimated_weekly_cost?: number
}

function groupByCategory(items: GroceryItemData[]): Record<string, GroceryItemData[]> {
  return items.reduce<Record<string, GroceryItemData[]>>((acc, item) => {
    const cat = item.food_category ?? "Other"
    ;(acc[cat] ??= []).push(item)
    return acc
  }, {})
}

const CATEGORY_ICONS: Record<string, string> = {
  "Grains & Bread": "🌾",
  "Beans & Legumes": "🫘",
  "Meat & Poultry": "🍗",
  "Dairy & Eggs": "🥛",
  "Seafood": "🐟",
  "Vegetables": "🥦",
  "Fruit": "🍎",
  "Fats & Oils": "🫙",
  "Other": "📦",
}

function Skeleton() {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      {Array.from({ length: 9 }).map((_, i) => (
        <div key={i} className="rounded-2xl border-2 border-emerald-100 bg-white p-4 animate-pulse space-y-3">
          <div className="h-4 bg-emerald-100 rounded-lg w-3/4" />
          <div className="h-3 bg-emerald-50 rounded-lg w-1/2" />
          <div className="flex gap-2 pt-2">
            {Array.from({ length: 4 }).map((_, j) => (
              <div key={j} className="h-3 bg-emerald-50 rounded-lg flex-1" />
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}

export default function GroceryList({ profile }: GroceryListProps) {
  const { data, isPending, isError, error, refetch } = useQuery<RecommendationsResponse>({
    queryKey: ["recommendations", profile],
    queryFn: () => api.get("/recommendations", { params: profile }).then((r) => r.data),
    enabled: !USE_MOCK,
    retry: 1,
    initialData: USE_MOCK ? MOCK_RESPONSE : undefined,
  })

  if (isPending) {
    return (
      <div className="w-full max-w-5xl mx-auto py-10 px-4 space-y-6">
        <div className="space-y-2">
          <div className="h-6 bg-emerald-100 rounded-lg w-48 animate-pulse" />
          <div className="h-4 bg-emerald-50 rounded-lg w-64 animate-pulse" />
        </div>
        <Skeleton />
      </div>
    )
  }

  if (isError) {
    return (
      <div className="flex flex-col items-center justify-center gap-4 py-20 text-center">
        <div className="w-16 h-16 rounded-full bg-red-100 flex items-center justify-center text-2xl">⚠️</div>
        <p className="text-lg font-bold text-red-600">Failed to load recommendations</p>
        <p className="text-sm text-emerald-600">
          {error instanceof Error ? error.message : "Unknown error"}
        </p>
        <Button variant="outline" onClick={() => refetch()}>Try again</Button>
      </div>
    )
  }

  const items = data?.items ?? []
  const totalCost = data?.estimated_weekly_cost

  if (items.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center gap-4 py-20 text-center">
        <div className="w-16 h-16 rounded-full bg-emerald-100 flex items-center justify-center text-2xl">🛒</div>
        <p className="text-lg font-bold text-emerald-900">No recommendations found</p>
        <p className="text-sm text-emerald-600">Try adjusting your dietary preferences or budget.</p>
      </div>
    )
  }

  const grouped = groupByCategory(items)

  return (
    <div className="w-full max-w-5xl mx-auto py-8 px-4 space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h2 className="text-2xl font-extrabold text-emerald-900">Your Grocery List</h2>
          <p className="text-sm text-emerald-600 mt-1">
            {items.length} items personalized for your health profile
          </p>
        </div>
        {totalCost != null && (
          <div className="bg-white rounded-2xl border-2 border-emerald-200 shadow-sm px-5 py-3 text-center">
            <p className="text-xs font-semibold text-emerald-500 uppercase tracking-wide">Est. weekly cost</p>
            <p className="text-3xl font-extrabold text-emerald-600">${totalCost.toFixed(2)}</p>
          </div>
        )}
      </div>

      {/* Items grouped by category */}
      {Object.entries(grouped).map(([category, catItems]) => (
        <section key={category} className="space-y-4">
          <div className="flex items-center gap-2 border-b-2 border-emerald-100 pb-3">
            <span className="text-xl">{CATEGORY_ICONS[category] ?? "📦"}</span>
            <h3 className="text-base font-bold text-emerald-800">{category}</h3>
            <span className="text-xs font-medium text-emerald-400 bg-emerald-50 rounded-full px-2 py-0.5">
              {catItems.length}
            </span>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {catItems.map((item) => (
              <GroceryItem key={item.fdc_id} item={item} />
            ))}
          </div>
        </section>
      ))}
    </div>
  )
}
