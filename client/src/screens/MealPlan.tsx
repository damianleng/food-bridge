import { useMemo, useState } from "react";
import { useApp } from "@/store/app";
import { generateGroceryList } from "@/lib/api";
import Spinner from "@/components/Spinner";
import ErrorAlert from "@/components/ErrorAlert";

interface DayPlan {
  day: string;
  meals: { name: string; description?: string }[];
}

interface ParsedPlan {
  coverage: { name: string; pct: number }[];
  days: DayPlan[];
  swaps: { food: string; reason: string }[];
  rawFallback?: string;
}

const NUTRIENT_LABELS: Record<string, string> = {
  calories_kcal: "Calories", protein_g: "Protein", fat_g: "Fat",
  saturated_fat_g: "Sat. Fat", carbohydrates_g: "Carbs", fiber_g: "Fiber",
  added_sugars_g: "Added Sugar", sodium_mg: "Sodium", potassium_mg: "Potassium",
  calcium_mg: "Calcium", iron_mg: "Iron", vitamin_c_mg: "Vitamin C",
  vitamin_d_iu: "Vitamin D", folate_mcg: "Folate", b12_mcg: "Vitamin B12",
  magnesium_mg: "Magnesium", zinc_mg: "Zinc",
};

const MEAL_META = [
  { label: "Breakfast", icon: "🌅", bg: "bg-amber-50" },
  { label: "Lunch",     icon: "☀️", bg: "bg-sky-50" },
  { label: "Dinner",    icon: "🌙", bg: "bg-indigo-50" },
];

function coverageColor(pct: number): string {
  if (pct >= 90) return "bg-green-500";
  if (pct >= 70) return "bg-yellow-400";
  if (pct >= 50) return "bg-orange-400";
  return "bg-red-500";
}

function coverageTextColor(pct: number): string {
  if (pct >= 90) return "text-green-700";
  if (pct >= 70) return "text-yellow-700";
  if (pct >= 50) return "text-orange-600";
  return "text-red-600";
}

function parseMealContent(raw: string): string {
  return raw
    .replace(/^[^\w\s]*\s*(breakfast|lunch|dinner)\s*[:\-–]\s*/i, "")
    .replace(/^[^\w\s]+\s*/, "")
    .trim();
}

function parseMealPlan(text: string): ParsedPlan {
  const result: ParsedPlan = { coverage: [], days: [], swaps: [] };
  if (!text) return result;

  const jsonMatch = text.match(/\{[\s\S]*\}/);
  if (jsonMatch) {
    try {
      const obj = JSON.parse(jsonMatch[0]) as Record<string, unknown>;

      const cov = (obj.nutrient_coverage ?? obj.coverage ?? obj.nutrients) as Record<string, unknown> | unknown[] | undefined;
      if (cov && typeof cov === "object" && !Array.isArray(cov)) {
        result.coverage = Object.entries(cov).map(([name, v]) => ({
          name: NUTRIENT_LABELS[name] ?? name,
          pct: typeof v === "number" ? v : Number(String(v).replace(/[^\d.]/g, "")) || 0,
        }));
      }

      const days = (obj.days ?? obj.plan ?? obj.meal_plan) as unknown[] | undefined;
      if (Array.isArray(days)) {
        result.days = days.map((d, i) => {
          const dd = d as Record<string, unknown>;
          return {
            day: String(dd.day ?? `Day ${i + 1}`),
            meals: ((dd.meals ?? []) as unknown[]).map((m) => {
              if (typeof m === "string") return { name: m };
              const mm = m as Record<string, unknown>;
              return { name: String(mm.name ?? mm.title ?? "Meal"), description: mm.description as string | undefined };
            }),
          };
        });
      }

      const swaps = (obj.swaps ?? obj.suggested_swaps) as unknown[] | undefined;
      if (Array.isArray(swaps)) {
        result.swaps = swaps.map((s) => {
          if (typeof s === "string") return { food: s, reason: "" };
          const ss = s as Record<string, unknown>;
          return { food: String(ss.food ?? ss.name ?? ""), reason: String(ss.reason ?? ss.gap ?? "") };
        });
      }

      if (result.days.length) return result;
    } catch { /* ignore */ }
  }

  const dayBlocks = text.split(/(?=Day\s*\d)/i).filter((b) => /Day\s*\d/i.test(b));
  if (dayBlocks.length) {
    result.days = dayBlocks.slice(0, 7).map((blk, i) => {
      const dayMatch = blk.match(/Day\s*\d+/i);
      const meals = blk.split(/\r?\n/).map((l) => l.trim()).filter((l) => /^[-*•]/.test(l)).slice(0, 3)
        .map((l) => ({ name: l.replace(/^[-*•]\s*/, "") }));
      return { day: dayMatch ? dayMatch[0] : `Day ${i + 1}`, meals };
    });
  }
  result.rawFallback = result.days.length ? undefined : text;
  return result;
}

const MealPlan = () => {
  const { mealPlanResponse, profileId, selectedFoods, setScreen, setResponse } = useApp();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeDay, setActiveDay] = useState(0);

  const plan = useMemo(() => parseMealPlan(mealPlanResponse), [mealPlanResponse]);

  const generateGrocery = async () => {
    if (!profileId) { setError("Profile not found. Please restart."); return; }
    setError(null);
    setLoading(true);
    try {
      const foods = selectedFoods.map((f) => ({ fdc_id: Number(f.fdc_id), name: f.name }));
      const result = await generateGroceryList(profileId, foods);
      setResponse("grocery", result);
      setScreen(5);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to generate list");
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center"><Spinner message="Building your grocery list..." /></div>;
  }

  const currentDay = plan.days[activeDay];

  return (
    <div className="min-h-screen flex flex-col bg-background">
      <header className="px-5 pt-8 pb-4 max-w-xl mx-auto w-full">
        <p className="fb-section-title">Step 4 of 5</p>
        <h1 className="text-3xl font-bold mt-1">Your 7-Day Plan</h1>
      </header>

      <main className="flex-1 max-w-xl mx-auto w-full px-5 pb-32 space-y-6">
        {error && <ErrorAlert message={error} onDismiss={() => setError(null)} />}

        {/* Day selector */}
        {plan.days.length > 0 && (
          <div className="flex gap-2 overflow-x-auto pb-1 -mx-1 px-1 scrollbar-hide">
            {plan.days.map((_d, i) => (
              <button
                key={i}
                type="button"
                onClick={() => setActiveDay(i)}
                className={`shrink-0 flex flex-col items-center justify-center w-14 h-14 border-2 border-foreground text-xs font-bold transition-colors
                  ${activeDay === i ? "bg-foreground text-background" : "bg-background text-foreground"}`}
              >
                <span className="text-[10px] font-normal opacity-70">DAY</span>
                <span className="text-lg leading-none">{i + 1}</span>
              </button>
            ))}
          </div>
        )}

        {/* Meals for active day */}
        {currentDay && (
          <section className="space-y-3">
            <h2 className="fb-section-title">{currentDay.day}</h2>
            <div className="space-y-3">
              {currentDay.meals.map((meal, i) => {
                const meta = MEAL_META[i] ?? MEAL_META[0];
                const content = parseMealContent(meal.name);
                return (
                  <div key={i} className={`border-2 border-foreground p-4 ${meta.bg}`}>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-lg">{meta.icon}</span>
                      <span className="text-xs font-bold uppercase tracking-widest text-muted-foreground">{meta.label}</span>
                    </div>
                    <p className="font-semibold text-base leading-snug">{content || meal.name}</p>
                    {meal.description && <p className="text-sm text-muted-foreground mt-1">{meal.description}</p>}
                  </div>
                );
              })}
            </div>
          </section>
        )}

        {/* Nutrient coverage */}
        {plan.coverage.length > 0 && (
          <section className="space-y-3">
            <h2 className="fb-section-title">Nutrient coverage</h2>
            <div className="grid grid-cols-2 gap-x-6 gap-y-3">
              {plan.coverage.map((c) => {
                const pct = Math.min(100, Math.max(0, c.pct));
                return (
                  <div key={c.name}>
                    <div className="flex justify-between text-xs mb-1">
                      <span className="text-muted-foreground truncate pr-1">{c.name}</span>
                      <span className={`font-bold tabular-nums shrink-0 ${coverageTextColor(c.pct)}`}>
                        {Math.round(c.pct)}%
                      </span>
                    </div>
                    <div className="h-1.5 bg-surface-2 rounded-full overflow-hidden">
                      <div className={`h-full rounded-full ${coverageColor(c.pct)}`} style={{ width: `${pct}%` }} />
                    </div>
                  </div>
                );
              })}
            </div>
          </section>
        )}

        {/* Suggested swaps */}
        {plan.swaps.length > 0 && (
          <section className="space-y-2">
            <h2 className="fb-section-title">💡 Suggested swaps</h2>
            {plan.swaps.map((s, i) => (
              <div key={i} className="border border-foreground p-3 flex items-start gap-3">
                <span className="text-lg shrink-0">🔄</span>
                <div>
                  <p className="font-semibold text-sm">{s.food}</p>
                  {s.reason && <p className="text-xs text-muted-foreground mt-0.5">{s.reason}</p>}
                </div>
              </div>
            ))}
          </section>
        )}

        {plan.rawFallback && (
          <div className="border border-foreground p-4 text-sm whitespace-pre-wrap">{plan.rawFallback}</div>
        )}
      </main>

      <footer className="fixed bottom-0 left-0 right-0 bg-background border-t border-foreground">
        <div className="max-w-xl mx-auto px-5 py-4 flex items-center gap-3">
          <button type="button" onClick={() => setScreen(3)} className="fb-btn-outline">Back</button>
          <button onClick={generateGrocery} className="fb-btn flex-1">Generate Grocery List</button>
        </div>
      </footer>
    </div>
  );
};

export default MealPlan;
