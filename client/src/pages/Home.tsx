import { useState } from "react"
import Form1, { type Form1Data } from "@/components/form1"
import Form2, { type Form2Data } from "@/components/form2"
import GroceryList from "@/components/grocerylist"
import { api } from "@/lib/api"
import { cn } from "@/lib/utils"

type Step = "form1" | "form2" | "list"

const STEPS = [
  { key: "form1", label: "Health Profile" },
  { key: "form2", label: "Preferences" },
  { key: "list",  label: "Your List" },
] as const

export default function Home() {
  const [step, setStep] = useState<Step>("form1")
  const [form1Data, setForm1Data] = useState<Form1Data | null>(null)
  const [profile, setProfile] = useState<Record<string, unknown>>({})

  const handleForm2Submit = (form2Data: Form2Data) => {
    const payload = { ...form1Data, ...form2Data } as Record<string, unknown>
    setProfile(payload)
    setStep("list")
    api.post("/submitdata", payload).catch((err) => console.error("Submission error:", err))
  }

  const stepIndex = STEPS.findIndex((s) => s.key === step)

  return (
    <div className="min-h-screen">
      {/* Hero header */}
      <header className="bg-gradient-to-br from-emerald-700 via-emerald-600 to-teal-500 text-white shadow-lg">
        <div className="max-w-4xl mx-auto px-6 py-8 text-center">
          <div className="flex items-center justify-center gap-2 mb-2">
            <span className="text-3xl">🌿</span>
            <h1 className="text-4xl font-extrabold tracking-tight">FoodBridge</h1>
          </div>
          <p className="text-emerald-100 text-lg">
            Affordable, personalized nutrition for every household.
          </p>

          {/* Step indicator */}
          <div className="flex items-center justify-center gap-0 mt-6">
            {STEPS.map((s, i) => (
              <div key={s.key} className="flex items-center">
                <div className="flex flex-col items-center gap-1">
                  <div
                    className={cn(
                      "w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold border-2 transition-all duration-300",
                      i < stepIndex
                        ? "bg-white text-emerald-700 border-white"
                        : i === stepIndex
                        ? "bg-amber-400 text-white border-amber-300 shadow-lg shadow-amber-400/50 scale-110"
                        : "bg-white/20 text-white/60 border-white/30"
                    )}
                  >
                    {i < stepIndex ? "✓" : i + 1}
                  </div>
                  <span
                    className={cn(
                      "text-xs font-medium transition-colors",
                      i === stepIndex ? "text-amber-300" : "text-emerald-200"
                    )}
                  >
                    {s.label}
                  </span>
                </div>
                {i < STEPS.length - 1 && (
                  <div
                    className={cn(
                      "w-16 h-0.5 mx-1 mb-5 transition-all duration-500",
                      i < stepIndex ? "bg-white" : "bg-white/25"
                    )}
                  />
                )}
              </div>
            ))}
          </div>
        </div>
      </header>

      {/* Page content */}
      <main className="max-w-4xl mx-auto">
        {step === "form1" && (
          <Form1 onSubmit={(data) => { setForm1Data(data); setStep("form2") }} />
        )}
        {step === "form2" && (
          <Form2 onSubmit={handleForm2Submit} />
        )}
        {step === "list" && (
          <GroceryList profile={profile} />
        )}
      </main>
    </div>
  )
}
