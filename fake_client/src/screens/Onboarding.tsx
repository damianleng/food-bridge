import { useState } from "react";
import { useApp, type Sex, type Activity, type Smoking } from "@/store/app";
import { chat } from "@/lib/api";
import ProgressBar from "@/components/ProgressBar";
import PillGroup from "@/components/PillGroup";
import Stepper from "@/components/Stepper";
import Spinner from "@/components/Spinner";
import ErrorAlert from "@/components/ErrorAlert";

const ACTIVITY: Activity[] = ["Sedentary", "Lightly Active", "Moderately Active", "Very Active", "Extra Active"];
const GOALS = ["Weight Loss", "Muscle Gain", "Weight Gain", "Maintenance"];
const CONDITIONS = ["Hypertension", "Diabetes", "Heart Disease", "None"];
const SMOKING: Smoking[] = ["Smoker", "Non-Smoker", "Former Smoker"];

const STEPS = 6;

const Onboarding = () => {
  const { profile, setProfile, setScreen, setResponse } = useApp();
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const next = () => setStep((s) => Math.min(STEPS, s + 1));
  const back = () => setStep((s) => Math.max(1, s - 1));

  const submit = async () => {
    setError(null);
    setLoading(true);
    try {
      const msg = `I want to set up my profile. Here are my details: height ${profile.height}cm, weight ${profile.weight}kg, age ${profile.age}, sex ${profile.sex}, activity level ${profile.activity}, health goals ${profile.goals.join(", ") || "none"}, health conditions ${profile.conditions.join(", ") || "none"}, smoking status ${profile.smoking}, medications ${profile.medications || "none"}, household size ${profile.adults} adults and ${profile.children} children.`;
      const res = await chat(msg);
      setResponse("profile", res.response);
      setScreen(2);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Spinner message="Setting up your profile..." />
      </div>
    );
  }

  const canContinue = (() => {
    switch (step) {
      case 1: return profile.height && profile.weight && profile.age && profile.sex;
      case 2: return !!profile.activity;
      case 3: return profile.goals.length > 0;
      case 4: return profile.conditions.length > 0;
      case 5: return !!profile.smoking;
      case 6: return true;
      default: return false;
    }
  })();

  return (
    <div className="min-h-screen flex flex-col">
      <header className="px-5 pt-6 pb-4 max-w-xl mx-auto w-full">
        <ProgressBar current={step} total={STEPS} />
      </header>

      <main className="flex-1 px-5 max-w-xl mx-auto w-full pb-32">
        {error && <div className="mb-4"><ErrorAlert message={error} onDismiss={() => setError(null)} /></div>}

        {step === 1 && (
          <section className="space-y-6">
            <h1 className="text-3xl font-bold">About you</h1>
            <p className="text-sm text-muted-foreground -mt-4">Basic measurements help us personalize your nutrition.</p>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Height (cm)"><input className="fb-input" inputMode="numeric" value={profile.height} onChange={(e) => setProfile({ height: e.target.value })} /></Field>
              <Field label="Weight (kg)"><input className="fb-input" inputMode="numeric" value={profile.weight} onChange={(e) => setProfile({ weight: e.target.value })} /></Field>
              <Field label="Age"><input className="fb-input" inputMode="numeric" value={profile.age} onChange={(e) => setProfile({ age: e.target.value })} /></Field>
              <Field label="Sex">
                <div className="grid grid-cols-2 border border-foreground h-12">
                  {(["Male", "Female"] as Sex[]).map((s) => (
                    <button key={s} type="button" onClick={() => setProfile({ sex: s })}
                      className={`text-sm font-medium ${profile.sex === s ? "bg-foreground text-background" : "bg-background text-foreground"}`}>
                      {s}
                    </button>
                  ))}
                </div>
              </Field>
            </div>
          </section>
        )}

        {step === 2 && (
          <section className="space-y-6">
            <h1 className="text-3xl font-bold">Activity level</h1>
            <p className="text-sm text-muted-foreground -mt-4">How active are you on a typical week?</p>
            <div className="flex flex-col gap-2">
              {ACTIVITY.map((a) => (
                <button key={a} type="button" onClick={() => setProfile({ activity: a })}
                  className={`h-12 border border-foreground text-sm font-medium px-4 text-left ${profile.activity === a ? "bg-foreground text-background" : "bg-background"}`}>
                  {a}
                </button>
              ))}
            </div>
          </section>
        )}

        {step === 3 && (
          <section className="space-y-6">
            <h1 className="text-3xl font-bold">Health goals</h1>
            <PillGroup options={GOALS} selected={profile.goals} onChange={(v) => setProfile({ goals: v })} />
          </section>
        )}

        {step === 4 && (
          <section className="space-y-6">
            <h1 className="text-3xl font-bold">Health conditions</h1>
            <PillGroup options={CONDITIONS} selected={profile.conditions} onChange={(v) => setProfile({ conditions: v })} />
          </section>
        )}

        {step === 5 && (
          <section className="space-y-6">
            <h1 className="text-3xl font-bold">Lifestyle</h1>
            <Field label="Smoking status">
              <div className="grid grid-cols-3 border border-foreground h-12">
                {SMOKING.map((s) => (
                  <button key={s} type="button" onClick={() => setProfile({ smoking: s })}
                    className={`text-xs sm:text-sm font-medium ${profile.smoking === s ? "bg-foreground text-background" : "bg-background"}`}>
                    {s}
                  </button>
                ))}
              </div>
            </Field>
            <Field label="Medications (optional)">
              <textarea className="fb-input min-h-[96px] py-3" value={profile.medications}
                onChange={(e) => setProfile({ medications: e.target.value })} placeholder="e.g. metformin, lisinopril" />
            </Field>
          </section>
        )}

        {step === 6 && (
          <section className="space-y-6">
            <h1 className="text-3xl font-bold">Household</h1>
            <p className="text-sm text-muted-foreground -mt-4">Who are we planning meals for?</p>
            <div className="space-y-3">
              <Stepper label="Adults" value={profile.adults} onChange={(n) => setProfile({ adults: n })} min={1} max={20} />
              <Stepper label="Children" value={profile.children} onChange={(n) => setProfile({ children: n })} min={0} max={20} />
            </div>
          </section>
        )}
      </main>

      <footer className="fixed bottom-0 left-0 right-0 bg-background border-t border-foreground">
        <div className="max-w-xl mx-auto px-5 py-4 flex items-center justify-between gap-3">
          <button type="button" onClick={back} disabled={step === 1} className="fb-btn-outline">Back</button>
          {step < STEPS ? (
            <button type="button" onClick={next} disabled={!canContinue} className="fb-btn flex-1">Continue</button>
          ) : (
            <button type="button" onClick={submit} disabled={!canContinue} className="fb-btn flex-1">Finish profile</button>
          )}
        </div>
      </footer>
    </div>
  );
};

const Field = ({ label, children }: { label: string; children: React.ReactNode }) => (
  <label className="block space-y-2">
    <span className="fb-section-title block">{label}</span>
    {children}
  </label>
);

export default Onboarding;
