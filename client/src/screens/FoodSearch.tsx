import { useState, useEffect } from "react";
import { useApp, type FoodItem } from "@/store/app";
import { searchFoods, generateMealPlan } from "@/lib/api";
import Spinner from "@/components/Spinner";
import ErrorAlert from "@/components/ErrorAlert";

const MP_STEPS = [
  { icon: "🥗", text: "Analyzing your food selections…"   },
  { icon: "📊", text: "Calculating nutrient coverage…"     },
  { icon: "🧬", text: "Matching your health profile…"      },
  { icon: "📅", text: "Designing your 7-day plan…"         },
  { icon: "⚖️",  text: "Balancing meals & variety…"        },
  { icon: "✨",  text: "Putting the finishing touches…"    },
];
const FLOAT_ICONS = [
  { emoji: "🥦", top: "8%",  left: "7%",  dur: 6.2, delay: 0    },
  { emoji: "🍎", top: "15%", left: "82%", dur: 7.5, delay: -2.1 },
  { emoji: "🐟", top: "72%", left: "12%", dur: 5.8, delay: -1.3 },
  { emoji: "🥚", top: "78%", left: "78%", dur: 6.9, delay: -3.4 },
  { emoji: "🫐", top: "42%", left: "91%", dur: 7.1, delay: -0.8 },
  { emoji: "🥕", top: "55%", left: "4%",  dur: 6.4, delay: -2.7 },
  { emoji: "🌽", top: "25%", left: "55%", dur: 8.0, delay: -4.0 },
  { emoji: "🍇", top: "88%", left: "48%", dur: 5.5, delay: -1.6 },
];
const GREEN = "#7ded7d";

function MealPlanLoader() {
  const [step, setStep] = useState(0);

  useEffect(() => {
    const t = setInterval(() => setStep(s => (s + 1) % MP_STEPS.length), 2500);
    return () => clearInterval(t);
  }, []);

  const { icon, text } = MP_STEPS[step];

  return (
    <div style={{
      minHeight: "100vh", display: "flex", flexDirection: "column",
      alignItems: "center", justifyContent: "center",
      background: "linear-gradient(160deg, hsl(150 60% 97%) 0%, hsl(150 40% 93%) 100%)",
      position: "relative", overflow: "hidden",
    }}>
      {/* Background radial glow */}
      <div style={{
        position: "absolute", width: 520, height: 520, borderRadius: "50%",
        background: `radial-gradient(circle, rgba(125,237,125,0.22) 0%, transparent 68%)`,
        top: "50%", left: "50%", transform: "translate(-50%,-50%)",
        pointerEvents: "none",
      }} />

      {/* Expanding pulse rings */}
      {[0, 1, 2].map(i => (
        <div key={i} style={{
          position: "absolute", width: 104, height: 104, borderRadius: "50%",
          border: `2px solid ${GREEN}`,
          animation: `mp-ring-expand 2.7s ease-out ${i * 0.9}s infinite`,
          pointerEvents: "none",
        }} />
      ))}

      {/* Floating background food icons */}
      {FLOAT_ICONS.map(({ emoji, top, left, dur, delay }, i) => (
        <div key={i} style={{
          position: "absolute", fontSize: "1.6rem",
          top, left,
          opacity: 0.35,
          animation: `mp-float ${dur}s ease-in-out ${delay}s infinite`,
          pointerEvents: "none",
        }}>
          {emoji}
        </div>
      ))}

      {/* Center bubble */}
      <div style={{
        position: "relative", zIndex: 10,
        width: 90, height: 90, borderRadius: "50%",
        background: `linear-gradient(135deg, ${GREEN} 0%, #3dc86e 100%)`,
        display: "flex", alignItems: "center", justifyContent: "center",
        fontSize: "2.3rem",
        boxShadow: `0 0 0 8px rgba(125,237,125,0.15), 0 0 40px rgba(125,237,125,0.4)`,
        animation: "mp-float 3s ease-in-out infinite",
      }}>
        <span key={step} style={{ animation: "mp-fade-up 0.3s ease-out" }}>{icon}</span>
      </div>

      {/* Headline */}
      <h2 style={{
        marginTop: "2rem", fontSize: "1.5rem", fontWeight: 700,
        letterSpacing: "-0.02em", color: "hsl(158 60% 18%)",
        background: `linear-gradient(90deg, hsl(158 60% 25%), ${GREEN}, hsl(158 60% 25%))`,
        backgroundSize: "200% auto",
        WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent",
        animation: "mp-shimmer 3s linear infinite",
      }}>
        Building your meal plan
      </h2>

      {/* Cycling step label */}
      <p key={step} style={{
        marginTop: "0.6rem", fontSize: "0.9rem",
        color: "hsl(158 20% 38%)", animation: "mp-fade-up 0.3s ease-out",
        minHeight: "1.3rem",
      }}>
        {text}
      </p>

      {/* Progress dots */}
      <div style={{ display: "flex", gap: 7, marginTop: "1.8rem", alignItems: "center" }}>
        {MP_STEPS.map((_, i) => (
          <div key={i} style={{
            height: 6, borderRadius: 3,
            width: i === step ? 24 : 6,
            background: i === step ? GREEN : "hsl(150 30% 82%)",
            transition: "all 0.35s cubic-bezier(0.4,0,0.2,1)",
            boxShadow: i === step ? `0 0 8px rgba(125,237,125,0.7)` : "none",
          }} />
        ))}
      </div>

      <p style={{ marginTop: "2.5rem", fontSize: "0.75rem", color: "hsl(158 12% 55%)" }}>
        This usually takes 15–30 seconds
      </p>
    </div>
  );
}

const DATA_TYPE_LABELS: Record<string, string> = {
  foundation_food:   "Foundation",
  sr_legacy_food:    "Standard",
  branded_food:      "Branded",
  survey_fndds_food: "Survey",
  sub_sample_food:   "Sample",
};

function scoreColor(score: number): string {
  if (score >= 70) return "bg-green-500 text-white";
  if (score >= 45) return "bg-yellow-400 text-black";
  return "bg-red-400 text-white";
}

function shortName(name: string): string {
  // Strip long marketing suffixes after the 3rd comma
  const parts = name.split(",");
  return parts.slice(0, 3).join(",").trim();
}

const FoodSearch = () => {
  const { setScreen, setResponse, selectedFoods, setSelectedFoods, profileId } = useApp();
  const [query, setQuery] = useState("");
  const [searching, setSearching] = useState(false);
  const [building, setBuilding] = useState(false);
  const [results, setResults] = useState<FoodItem[]>([]);
  const [searched, setSearched] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const search = async (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!query.trim()) return;
    setError(null);
    setSearching(true);
    try {
      const foods = await searchFoods(query.trim(), profileId || undefined);
      setResults(foods.map((f) => ({ ...f, data_type: f.data_type ?? undefined })));
      setSearched(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Search failed");
    } finally {
      setSearching(false);
    }
  };

  const toggle = (f: FoodItem) => {
    const exists = selectedFoods.find((s) => s.fdc_id === f.fdc_id);
    if (exists) setSelectedFoods(selectedFoods.filter((s) => s.fdc_id !== f.fdc_id));
    else setSelectedFoods([...selectedFoods, f]);
  };

  const isSelected = (f: FoodItem) => !!selectedFoods.find((s) => s.fdc_id === f.fdc_id);

  const buildPlan = async () => {
    if (!profileId) { setError("Profile not found. Please restart."); return; }
    setError(null);
    setBuilding(true);
    try {
      const foods = selectedFoods.map((f) => ({ fdc_id: Number(f.fdc_id), name: f.name }));
      const result = await generateMealPlan(profileId, foods);
      setResponse("mealPlan", result);
      setScreen(4);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to build plan");
    } finally {
      setBuilding(false);
    }
  };

  if (building) return <MealPlanLoader />;

  const needed = Math.max(0, 3 - selectedFoods.length);

  return (
    <div className="min-h-screen flex flex-col bg-background">
      <header className="px-5 pt-8 pb-3 max-w-xl mx-auto w-full">
        <p className="fb-section-title">Step 3 of 5</p>
        <h1 className="text-3xl font-bold mt-1">Find foods</h1>
        <p className="text-sm text-muted-foreground mt-1">
          {needed > 0 ? `Pick at least ${needed} more food${needed > 1 ? "s" : ""}.` : "Great selection! Add more or build your plan."}
        </p>
      </header>

      {/* Search bar */}
      <div className="px-5 max-w-xl mx-auto w-full">
        <form onSubmit={search} className="flex gap-2">
          <input
            className="fb-input flex-1"
            placeholder="e.g. chicken, brown rice, tofu..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <button type="submit" className="fb-btn px-5" disabled={searching || !query.trim()}>
            {searching ? "…" : "Search"}
          </button>
        </form>
      </div>

      {/* Selected chips */}
      {selectedFoods.length > 0 && (
        <div className="px-5 max-w-xl mx-auto w-full mt-3">
          <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-hide">
            {selectedFoods.map((f) => (
              <button
                key={f.fdc_id}
                type="button"
                onClick={() => toggle(f)}
                className="shrink-0 flex items-center gap-1.5 bg-foreground text-background text-xs font-medium px-3 py-1.5 rounded-full"
              >
                <span className="max-w-[120px] truncate">{shortName(f.name)}</span>
                <span className="opacity-70 text-sm leading-none">×</span>
              </button>
            ))}
          </div>
        </div>
      )}

      <main className="flex-1 max-w-xl mx-auto w-full px-5 pt-4 pb-32">
        {error && <div className="mb-4"><ErrorAlert message={error} onDismiss={() => setError(null)} /></div>}
        {searching && <Spinner message="Searching foods..." />}

        {!searching && searched && results.length === 0 && (
          <p className="text-sm text-muted-foreground text-center py-12">No results for "{query}". Try a simpler term.</p>
        )}

        {!searching && results.length === 0 && !query && (
          <div className="text-center py-12 space-y-2">
            <p className="text-4xl">🥦</p>
            <p className="text-sm text-muted-foreground">Search for foods above to get started.</p>
          </div>
        )}

        {/* Results grid */}
        <div className="grid grid-cols-2 gap-3">
          {results.map((f, i) => {
            const sel = isSelected(f);
            const label = DATA_TYPE_LABELS[f.data_type ?? ""] ?? f.data_type ?? "";
            const name = shortName(f.name);
            return (
              <button
                key={`${f.fdc_id}-${i}`}
                type="button"
                onClick={() => toggle(f)}
                className={`text-left border-2 p-3 flex flex-col gap-2 transition-colors relative
                  ${sel ? "border-foreground bg-foreground text-background" : "border-foreground bg-background text-foreground"}`}
              >
                {/* Score badge */}
                {typeof f.score === "number" && (
                  <span className={`absolute top-2 right-2 text-[11px] font-extrabold px-1.5 py-0.5 rounded ${sel ? "bg-background text-foreground" : scoreColor(f.score)}`}>
                    {Math.round(f.score)}
                  </span>
                )}

                {/* Checkmark */}
                {sel && (
                  <span className="absolute top-2 left-2 text-background text-sm leading-none">✓</span>
                )}

                {/* Name */}
                <p className={`text-sm font-semibold leading-snug line-clamp-2 mt-4 ${sel ? "text-background" : ""}`}>
                  {name}
                </p>

                {/* Tags */}
                <div className="flex flex-wrap gap-1">
                  {label && (
                    <span className={`text-[10px] px-1.5 py-0.5 font-medium uppercase tracking-wide
                      ${sel ? "bg-white/20 text-background" : "bg-surface-2 text-muted-foreground"}`}>
                      {label}
                    </span>
                  )}
                  {f.top_nutrients?.slice(0, 2).map((n) => (
                    <span key={n} className={`text-[10px] px-1.5 py-0.5
                      ${sel ? "bg-white/20 text-background" : "bg-surface text-muted-foreground"}`}>
                      {n}
                    </span>
                  ))}
                </div>
              </button>
            );
          })}
        </div>
      </main>

      <footer className="fixed bottom-0 left-0 right-0 bg-background border-t border-foreground">
        <div className="max-w-xl mx-auto px-5 py-4 flex items-center gap-3">
          <button type="button" onClick={() => setScreen(2)} className="fb-btn-outline">Back</button>
          <button onClick={buildPlan} disabled={selectedFoods.length < 3} className="fb-btn flex-1">
            {selectedFoods.length < 3
              ? `Select ${needed} more`
              : `Build Plan (${selectedFoods.length})`}
          </button>
        </div>
      </footer>
    </div>
  );
};

export default FoodSearch;