import { useState } from "react";
import { useApp } from "@/store/app";
import { chat } from "@/lib/api";
import PillGroup from "@/components/PillGroup";
import Spinner from "@/components/Spinner";
import ErrorAlert from "@/components/ErrorAlert";

const DIETS = ["Vegetarian", "Vegan", "Gluten Free", "Dairy Free", "Nut Free", "Low Sodium", "Low Carb", "Keto", "Halal", "Kosher"];
const ALLERGIES = ["Peanuts", "Shellfish", "Dairy", "Eggs", "Wheat", "Soy", "Tree Nuts", "Fish"];
const CUISINES = ["Mediterranean", "Asian", "Mexican", "American", "Italian", "Middle Eastern"];

const Preferences = () => {
  const { preferences, setPreferences, setScreen, setResponse } = useApp();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async () => {
    setError(null);
    setLoading(true);
    try {
      const msg = `My preferences: weekly budget $${preferences.budget || "0"}, zip code ${preferences.zip}, dietary preferences ${preferences.diet.join(", ") || "none"}, allergies ${preferences.allergies.join(", ") || "none"}, cuisine preferences ${preferences.cuisines.join(", ") || "none"}, WIC eligible: ${preferences.wic ? "yes" : "no"}.`;
      const res = await chat(msg);
      setResponse("preferences", res.response);
      setScreen(3);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center"><Spinner message="Saving your preferences..." /></div>;
  }

  const canSubmit = preferences.budget && preferences.zip;

  return (
    <div className="min-h-screen flex flex-col">
      <header className="px-5 pt-8 pb-4 max-w-xl mx-auto w-full">
        <p className="fb-section-title">Step 2 of 5</p>
        <h1 className="text-3xl font-bold mt-2">Preferences</h1>
        <p className="text-sm text-muted-foreground mt-1">Budget, location, and what you like to eat.</p>
      </header>

      <main className="flex-1 max-w-xl mx-auto w-full px-5 pb-32 space-y-8">
        {error && <ErrorAlert message={error} onDismiss={() => setError(null)} />}

        <Section title="Budget & location">
          <div className="grid grid-cols-2 gap-3">
            <label className="space-y-2">
              <span className="fb-section-title block">Weekly budget</span>
              <div className="relative">
                <span className="absolute left-4 top-1/2 -translate-y-1/2 text-sm">$</span>
                <input className="fb-input pl-8" inputMode="decimal" value={preferences.budget}
                  onChange={(e) => setPreferences({ budget: e.target.value })} placeholder="150" />
              </div>
            </label>
            <label className="space-y-2">
              <span className="fb-section-title block">Zip code</span>
              <input className="fb-input" value={preferences.zip}
                onChange={(e) => setPreferences({ zip: e.target.value })} placeholder="10001" />
            </label>
          </div>
        </Section>

        <Section title="Dietary preferences">
          <PillGroup options={DIETS} selected={preferences.diet} onChange={(v) => setPreferences({ diet: v })} />
        </Section>

        <Section title="Allergies">
          <PillGroup options={ALLERGIES} selected={preferences.allergies} onChange={(v) => setPreferences({ allergies: v })} />
        </Section>

        <Section title="Cuisine preferences">
          <PillGroup options={CUISINES} selected={preferences.cuisines} onChange={(v) => setPreferences({ cuisines: v })} />
        </Section>

        <Section title="WIC eligibility">
          <button type="button" onClick={() => setPreferences({ wic: !preferences.wic })}
            className="w-full h-14 border border-foreground flex items-center justify-between px-4">
            <span className="text-sm text-left">Pregnant, infant, or child in household?</span>
            <span className={`w-12 h-7 border border-foreground relative transition-colors ${preferences.wic ? "bg-foreground" : "bg-background"}`}>
              <span className={`absolute top-0.5 ${preferences.wic ? "right-0.5 bg-background" : "left-0.5 bg-foreground"} w-5 h-5 transition-all`} />
            </span>
          </button>
        </Section>
      </main>

      <footer className="fixed bottom-0 left-0 right-0 bg-background border-t border-foreground">
        <div className="max-w-xl mx-auto px-5 py-4">
          <button onClick={submit} disabled={!canSubmit} className="fb-btn w-full">Continue</button>
        </div>
      </footer>
    </div>
  );
};

const Section = ({ title, children }: { title: string; children: React.ReactNode }) => (
  <section className="space-y-3">
    <h2 className="fb-section-title">{title}</h2>
    {children}
  </section>
);

export default Preferences;
