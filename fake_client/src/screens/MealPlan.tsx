import { useMemo, useState } from "react";
import { useApp } from "@/store/app";
import { chat } from "@/lib/api";
import Spinner from "@/components/Spinner";
import ErrorAlert from "@/components/ErrorAlert";

interface NutrientCoverage {
  name: string;
  pct: number;
}

interface DayPlan {
  day: string;
  meals: { name: string; description?: string }[];
}

interface Swap {
  food: string;
  reason: string;
}

interface ParsedPlan {
  coverage: NutrientCoverage[];
  days: DayPlan[];
  swaps: Swap[];
  rawFallback?: string;
}

function parseMealPlan(text: string): ParsedPlan {
  const result: ParsedPlan = { coverage: [], days: [], swaps: [] };
  if (!text) return result;

  // Try JSON object embedded in response
  const jsonMatch = text.match(/\{[\s\S]*\}/);
  if (jsonMatch) {
    try {
      const obj = JSON.parse(jsonMatch[0]) as Record<string, unknown>;

      const cov = (obj.nutrient_coverage ?? obj.coverage ?? obj.nutrients) as Record<string, unknown> | unknown[] | undefined;
      if (cov && typeof cov === "object" && !Array.isArray(cov)) {
        result.coverage = Object.entries(cov).map(([name, v]) => ({
          name,
          pct: typeof v === "number" ? v : Number(String(v).replace(/[^\d.]/g, "")) || 0,
        }));
      } else if (Array.isArray(cov)) {
        result.coverage = (cov as Record<string, unknown>[]).map((c) => ({
          name: String(c.name ?? c.nutrient ?? ""),
          pct: typeof c.pct === "number" ? c.pct : (typeof c.percent === "number" ? c.percent : Number(c.value) || 0),
        }));
      }

      const days = (obj.days ?? obj.plan ?? obj.meal_plan) as unknown[] | undefined;
      if (Array.isArray(days)) {
        result.days = days.map((d, i) => {
          const dd = d as Record<string, unknown>;
          const meals = (dd.meals ?? []) as unknown[];
          return {
            day: String(dd.day ?? `Day ${i + 1}`),
            meals: meals.map((m) => {
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

      if (result.coverage.length || result.days.length) return result;
    } catch { /* ignore */ }
  }

  // Plain-text fallback: split by "Day N"
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
  const { mealPlanResponse, setScreen, setResponse } = useApp();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [openDay, setOpenDay] = useState<number | null>(0);

  const plan = useMemo(() => parseMealPlan(mealPlanResponse), [mealPlanResponse]);

  const generateGrocery = async () => {
    setError(null);
    setLoading(true);
    try {
      const res = await chat("Generate my grocery list from this meal plan.");
      setResponse("grocery", res.response);
      setScreen(5);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to generate list");
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center"><Spinner message="Generating your grocery list..." /></div>;
  }

  return (
    <div className="min-h-screen flex flex-col">
      <header className="px-5 pt-8 pb-4 max-w-xl mx-auto w-full">
        <p className="fb-section-title">Step 4 of 5</p>
        <h1 className="text-3xl font-bold mt-2">Your 7-Day Meal Plan</h1>
      </header>

      <main className="flex-1 max-w-xl mx-auto w-full px-5 pb-32 space-y-8">
        {error && <ErrorAlert message={error} onDismiss={() => setError(null)} />}

        {plan.coverage.length > 0 && (
          <section className="space-y-3">
            <h2 className="fb-section-title">Nutrient coverage</h2>
            <div className="space-y-2.5">
              {plan.coverage.map((c) => {
                const flagged = c.pct < 50;
                const pct = Math.min(100, Math.max(0, c.pct));
                return (
                  <div key={c.name}>
                    <div className="flex justify-between text-sm mb-1">
                      <span className={flagged ? "font-bold" : ""}>{c.name}</span>
                      <span className={`tabular-nums ${flagged ? "font-bold" : "text-muted-foreground"}`}>{Math.round(c.pct)}%</span>
                    </div>
                    <div className="h-2 bg-surface-2">
                      <div className="h-full bg-foreground" style={{ width: `${pct}%` }} />
                    </div>
                  </div>
                );
              })}
            </div>
          </section>
        )}

        {plan.days.length > 0 && (
          <section className="space-y-2">
            <h2 className="fb-section-title">7-day plan</h2>
            <div className="border border-foreground divide-y divide-foreground">
              {plan.days.map((d, i) => {
                const open = openDay === i;
                return (
                  <div key={`${d.day}-${i}`}>
                    <button onClick={() => setOpenDay(open ? null : i)}
                      className="w-full flex items-center justify-between px-4 h-12 text-left">
                      <span className="font-semibold">{d.day}</span>
                      <span className="text-lg leading-none">{open ? "−" : "+"}</span>
                    </button>
                    {open && (
                      <div className="px-4 pb-4 space-y-3 bg-surface">
                        {d.meals.length === 0 && <p className="text-sm text-muted-foreground">No meals listed.</p>}
                        {d.meals.map((m, j) => (
                          <div key={j} className="text-sm">
                            <p className="font-semibold">{m.name}</p>
                            {m.description && <p className="text-muted-foreground mt-0.5">{m.description}</p>}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </section>
        )}

        {plan.swaps.length > 0 && (
          <section className="bg-surface border border-foreground p-4 space-y-2">
            <p className="font-semibold text-sm">💡 Suggested swaps to improve coverage</p>
            <ul className="space-y-1 text-sm">
              {plan.swaps.map((s, i) => (
                <li key={i}><span className="font-medium">{s.food}</span>{s.reason && <span className="text-muted-foreground"> — {s.reason}</span>}</li>
              ))}
            </ul>
          </section>
        )}

        {plan.rawFallback && (
          <div className="border border-foreground p-4 text-sm whitespace-pre-wrap">{plan.rawFallback}</div>
        )}
      </main>

      <footer className="fixed bottom-0 left-0 right-0 bg-background border-t border-foreground">
        <div className="max-w-xl mx-auto px-5 py-4">
          <button onClick={generateGrocery} className="fb-btn w-full">Generate Grocery List</button>
        </div>
      </footer>
    </div>
  );
};

export default MealPlan;
