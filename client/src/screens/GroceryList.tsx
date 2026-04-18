import { useMemo, useState } from "react";
import { useApp } from "@/store/app";
import { resetSession } from "@/lib/api";
import Spinner from "@/components/Spinner";

interface GroceryItem {
  name: string;
  brand?: string;
  quantity?: string;
  price?: number;
  source?: "live" | "estimate";
  category?: string;
}

interface ParsedGrocery {
  items: GroceryItem[];
  total: number;
  rawFallback?: string;
}

function parseItem(i: Record<string, unknown>, category?: string): GroceryItem {
  const priceRaw = i.estimated_unit_price_usd ?? i.price ?? i.estimated_price ?? i.cost;
  const price = typeof priceRaw === "number" ? priceRaw : Number(String(priceRaw ?? "").replace(/[^\d.]/g, "")) || 0;
  const src = String(i.price_source ?? i.source ?? "").toLowerCase();
  const qty = i.quantity_needed ?? i.quantity;
  return {
    name: String(i.description ?? i.name ?? i.food ?? "Item"),
    brand: (i.brand_name ?? i.brand) as string | undefined,
    quantity: qty != null ? `x${qty}` : undefined,
    price,
    source: src.includes("open") || src.includes("live") ? "live" : src.includes("est") ? "estimate" : undefined,
    category,
  };
}

function parseGrocery(text: string): ParsedGrocery {
  const result: ParsedGrocery = { items: [], total: 0 };
  if (!text) return result;

  const jsonMatch = text.match(/\{[\s\S]*\}/);
  if (jsonMatch) {
    try {
      const obj = JSON.parse(jsonMatch[0]) as Record<string, unknown>;

      const totalRaw = obj.total_estimated_cost_usd ?? obj.total ?? obj.estimated_total ?? obj.total_cost;
      result.total = typeof totalRaw === "number" ? totalRaw : Number(String(totalRaw ?? "").replace(/[^\d.]/g, "")) || 0;

      // Case 1: grocery_list is an object keyed by category
      const groceryList = obj.grocery_list ?? obj.items ?? obj.list;
      if (groceryList && typeof groceryList === "object" && !Array.isArray(groceryList)) {
        for (const [cat, catItems] of Object.entries(groceryList as Record<string, unknown>)) {
          if (Array.isArray(catItems)) {
            for (const it of catItems) {
              result.items.push(parseItem(it as Record<string, unknown>, cat));
            }
          }
        }
        if (result.items.length) return result;
      }

      // Case 2: flat array
      if (Array.isArray(groceryList)) {
        result.items = groceryList.map((it) => parseItem(it as Record<string, unknown>));
        if (result.items.length) return result;
      }
    } catch { /* ignore */ }
  }

  result.rawFallback = text;
  return result;
}

const CATEGORY_ICONS: Record<string, string> = {
  "Meat & Seafood": "🍗", "Meat": "🍗", "Seafood": "🐟",
  "Dairy & Eggs": "🥛", "Dairy": "🥛", "Eggs": "🥚",
  "Produce": "🥦", "Vegetables": "🥦", "Fruit": "🍎",
  "Grains & Legumes": "🌾", "Grains": "🌾", "Legumes": "🫘",
  "Beans & Legumes": "🫘", "Snacks": "🍿", "Beverages": "🧃",
  "Frozen": "🧊", "Fats & Oils": "🫙", "Other": "📦",
};

const categoryIcon = (cat: string) =>
  CATEGORY_ICONS[cat] ?? Object.entries(CATEGORY_ICONS).find(([k]) => cat.toLowerCase().includes(k.toLowerCase()))?.[1] ?? "🛒";

const GroceryList = () => {
  const { groceryResponse, preferences, reset } = useApp();
  const [resetting, setResetting] = useState(false);

  const parsed = useMemo(() => parseGrocery(groceryResponse), [groceryResponse]);
  const budget = Number(preferences.budget) || 0;
  const total = parsed.total || parsed.items.reduce((s, i) => s + (i.price ?? 0), 0);
  const within = budget > 0 ? total <= budget : true;
  const pct = budget > 0 ? Math.min(100, (total / budget) * 100) : 0;

  const grouped = useMemo(() => {
    const map = new Map<string, GroceryItem[]>();
    for (const it of parsed.items) {
      const cat = it.category || "Other";
      if (!map.has(cat)) map.set(cat, []);
      map.get(cat)!.push(it);
    }
    return Array.from(map.entries());
  }, [parsed.items]);

  const startOver = async () => {
    setResetting(true);
    try {
      await resetSession();
      reset();
    } finally {
      setResetting(false);
    }
  };

  if (resetting) {
    return <div className="min-h-screen flex items-center justify-center"><Spinner message="Resetting..." /></div>;
  }

  return (
    <div className="min-h-screen flex flex-col">
      <header className="px-5 pt-8 pb-4 max-w-xl mx-auto w-full">
        <p className="fb-section-title">Step 5 of 5</p>
        <div className="mt-2 flex items-start justify-between gap-4">
          <h1 className="text-3xl font-bold">Your Grocery List</h1>
          <p className="text-2xl font-extrabold tabular-nums">${total.toFixed(2)}</p>
        </div>

        {budget > 0 && (
          <div className="mt-5 space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Budget ${budget.toFixed(0)}</span>
              <span className="font-bold">{within ? "Within budget ✓" : "Over budget ✗"}</span>
            </div>
            <div className="h-2 bg-surface-2">
              <div className="h-full bg-foreground" style={{ width: `${pct}%` }} />
            </div>
          </div>
        )}
      </header>

      <main className="flex-1 max-w-xl mx-auto w-full px-5 pb-32 pt-4 space-y-8">
        {parsed.rawFallback && (
          <div className="border border-foreground p-4 text-sm whitespace-pre-wrap">{parsed.rawFallback}</div>
        )}

        {grouped.map(([cat, items]) => (
          <section key={cat} className="space-y-3">
            <div className="flex items-baseline justify-between border-b border-foreground pb-2">
              <h2 className="font-bold text-lg">{categoryIcon(cat)} {cat}</h2>
              <span className="text-xs text-muted-foreground tabular-nums">{items.length} item{items.length === 1 ? "" : "s"}</span>
            </div>
            <ul className="divide-y divide-surface-2">
              {items.map((it, i) => (
                <li key={i} className="py-3 flex items-start justify-between gap-4">
                  <div className="min-w-0 flex-1">
                    <p className="font-semibold text-sm">{it.name}</p>
                    {it.brand && <p className="text-xs text-muted-foreground">{it.brand}</p>}
                    <div className="mt-1 flex items-center gap-2">
                      {it.quantity && <span className="text-xs text-muted-foreground">{it.quantity}</span>}
                      {it.source && (
                        <span className={`text-[10px] uppercase tracking-wider px-1.5 py-0.5 ${it.source === "live" ? "bg-foreground text-background" : "bg-surface-2 text-foreground"}`}>
                          {it.source === "live" ? "live price" : "estimate"}
                        </span>
                      )}
                    </div>
                  </div>
                  {typeof it.price === "number" && (
                    <span className="text-sm font-semibold tabular-nums shrink-0">${it.price.toFixed(2)}</span>
                  )}
                </li>
              ))}
            </ul>
          </section>
        ))}
      </main>

      <footer className="fixed bottom-0 left-0 right-0 bg-background border-t border-foreground">
        <div className="max-w-xl mx-auto px-5 py-4">
          <button onClick={startOver} className="fb-btn w-full">Start Over</button>
        </div>
      </footer>
    </div>
  );
};

export default GroceryList;
