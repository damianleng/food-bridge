import { useState } from "react";
import { useApp, type FoodItem } from "@/store/app";
import { chat } from "@/lib/api";
import Spinner from "@/components/Spinner";
import ErrorAlert from "@/components/ErrorAlert";

// Try hard to extract a useful food list from the assistant's response.
// Accepts JSON arrays embedded in text, or falls back to bullet/line parsing.
function parseFoods(text: string): FoodItem[] {
  if (!text) return [];

  // 1. Look for a JSON array
  const jsonMatch = text.match(/\[\s*\{[\s\S]*?\}\s*\]/);
  if (jsonMatch) {
    try {
      const arr = JSON.parse(jsonMatch[0]);
      if (Array.isArray(arr)) {
        return arr.map((it: Record<string, unknown>) => ({
          fdc_id: (it.fdc_id ?? it.fdcId ?? it.id) as string | number | undefined,
          name: String(it.name ?? it.description ?? it.food ?? "Unknown"),
          data_type: (it.data_type ?? it.dataType ?? it.type) as string | undefined,
          score: typeof it.score === "number" ? it.score : (typeof it.nutrient_density === "number" ? it.nutrient_density : undefined),
          top_nutrients: Array.isArray(it.top_nutrients) ? (it.top_nutrients as string[]) : (Array.isArray(it.nutrients) ? (it.nutrients as string[]).slice(0, 3) : undefined),
        }));
      }
    } catch { /* ignore */ }
  }

  // 2. Fallback: parse bullet lines like "- Chicken breast (Foundation) — score 87"
  const lines = text.split(/\r?\n/).map((l) => l.trim()).filter(Boolean);
  const items: FoodItem[] = [];
  for (const line of lines) {
    const m = line.match(/^[-*•\d.)]+\s*(.+)$/);
    if (!m) continue;
    const body = m[1];
    const scoreMatch = body.match(/(\d{1,3})\s*(?:\/\s*100)?\s*$/);
    const typeMatch = body.match(/\(([^)]+)\)/);
    const name = body.replace(/\(([^)]+)\)/, "").replace(/\s*[—\-:]\s*score.*$/i, "").replace(/\s*\d{1,3}\s*(?:\/\s*100)?\s*$/, "").trim();
    if (name.length < 2) continue;
    items.push({
      name,
      data_type: typeMatch?.[1],
      score: scoreMatch ? Number(scoreMatch[1]) : undefined,
    });
    if (items.length >= 12) break;
  }
  return items;
}

const FoodSearch = () => {
  const { setScreen, setResponse, selectedFoods, setSelectedFoods } = useApp();
  const [query, setQuery] = useState("");
  const [searching, setSearching] = useState(false);
  const [building, setBuilding] = useState(false);
  const [results, setResults] = useState<FoodItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [rawText, setRawText] = useState("");

  const search = async (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!query.trim()) return;
    setError(null);
    setSearching(true);
    try {
      const res = await chat(`Search for foods matching: ${query}. Then score them by nutrient density for my profile.`);
      setRawText(res.response);
      const parsed = parseFoods(res.response);
      setResults(parsed);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Search failed");
    } finally {
      setSearching(false);
    }
  };

  const toggle = (f: FoodItem) => {
    const exists = selectedFoods.find((s) => s.name === f.name && s.fdc_id === f.fdc_id);
    if (exists) setSelectedFoods(selectedFoods.filter((s) => !(s.name === f.name && s.fdc_id === f.fdc_id)));
    else setSelectedFoods([...selectedFoods, f]);
  };

  const isSelected = (f: FoodItem) => !!selectedFoods.find((s) => s.name === f.name && s.fdc_id === f.fdc_id);

  const buildPlan = async () => {
    setError(null);
    setBuilding(true);
    try {
      const list = selectedFoods.map((f) => f.fdc_id ? `${f.name} (fdc_id: ${f.fdc_id})` : f.name).join(", ");
      const res = await chat(`Build a 7-day meal plan using these foods: ${list}. Check my budget and optimize for my daily values.`);
      setResponse("mealPlan", res.response);
      setScreen(4);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to build plan");
    } finally {
      setBuilding(false);
    }
  };

  if (building) {
    return <div className="min-h-screen flex items-center justify-center"><Spinner message="Optimizing your meal plan..." /></div>;
  }

  return (
    <div className="min-h-screen flex flex-col">
      <header className="px-5 pt-8 pb-4 max-w-xl mx-auto w-full">
        <p className="fb-section-title">Step 3 of 5</p>
        <h1 className="text-3xl font-bold mt-2">Find foods</h1>
        <p className="text-sm text-muted-foreground mt-1">Pick at least 3 foods to base your plan on.</p>
      </header>

      <div className="px-5 max-w-xl mx-auto w-full">
        <form onSubmit={search} className="flex gap-2">
          <input className="fb-input flex-1" placeholder="Search foods e.g. chicken breast, oat milk"
            value={query} onChange={(e) => setQuery(e.target.value)} />
          <button type="submit" className="fb-btn px-6" disabled={searching || !query.trim()}>
            {searching ? "..." : "Search"}
          </button>
        </form>
      </div>

      <main className="flex-1 max-w-xl mx-auto w-full px-5 pt-6 pb-32 space-y-3">
        {error && <ErrorAlert message={error} onDismiss={() => setError(null)} />}
        {searching && <Spinner message="Searching foods..." />}

        {!searching && results.length === 0 && rawText && (
          <div className="border border-foreground p-4 text-sm whitespace-pre-wrap">{rawText}</div>
        )}

        {results.map((f, i) => {
          const sel = isSelected(f);
          return (
            <button key={`${f.name}-${i}`} type="button" onClick={() => toggle(f)}
              className={`w-full text-left border border-foreground p-4 flex items-start gap-4 ${sel ? "bg-surface" : "bg-background"}`}>
              <span className={`mt-1 w-5 h-5 border border-foreground flex items-center justify-center shrink-0 ${sel ? "bg-foreground text-background" : ""}`}>
                {sel && "✓"}
              </span>
              <div className="flex-1 min-w-0">
                <div className="flex items-baseline justify-between gap-3">
                  <h3 className="font-bold text-base truncate">{f.name}</h3>
                  {typeof f.score === "number" && (
                    <span className="text-2xl font-extrabold tabular-nums shrink-0">{Math.round(f.score)}</span>
                  )}
                </div>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {f.data_type && (
                    <span className="text-[11px] uppercase tracking-wider px-2 py-0.5 bg-surface-2 text-foreground">{f.data_type}</span>
                  )}
                  {f.top_nutrients?.slice(0, 3).map((n) => (
                    <span key={n} className="text-[11px] px-2 py-0.5 bg-surface text-muted-foreground">{n}</span>
                  ))}
                </div>
              </div>
            </button>
          );
        })}
      </main>

      <footer className="fixed bottom-0 left-0 right-0 bg-background border-t border-foreground">
        <div className="max-w-xl mx-auto px-5 py-4 flex items-center gap-3">
          <span className="text-xs text-muted-foreground tabular-nums">{selectedFoods.length} selected</span>
          <button onClick={buildPlan} disabled={selectedFoods.length < 3} className="fb-btn flex-1">
            Build My Meal Plan
          </button>
        </div>
      </footer>
    </div>
  );
};

export default FoodSearch;
