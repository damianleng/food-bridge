import { useState } from "react"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

const SEX_OPTIONS = ["Male", "Female", "Non-binary", "Prefer not to say"]
const ACTIVITY_OPTIONS = [
  "Sedentary (little or no exercise)",
  "Lightly active (1–3 days/week)",
  "Moderately active (3–5 days/week)",
  "Very active (6–7 days/week)",
  "Extremely active (physical job + exercise)",
]
const SMOKING_OPTIONS = ["Never smoked", "Former smoker", "Current smoker"]
const HEALTH_GOAL_OPTIONS = [
  "Lose weight", "Gain muscle", "Manage blood sugar", "Lower blood pressure",
  "Lower cholesterol", "Improve energy", "Eat more affordably",
  "Support pregnancy / breastfeeding", "Support child nutrition",
]
const HEALTH_CONDITION_OPTIONS = [
  "Type 2 Diabetes", "Pre-diabetes", "Hypertension", "High cholesterol",
  "Heart disease", "Kidney disease", "Celiac disease / Gluten intolerance",
  "Iron-deficiency anemia", "Obesity", "Pregnancy", "Lactating",
]
const MEDICATION_OPTIONS = [
  "Metformin (diabetes)", "Insulin (diabetes)", "Statins (cholesterol)",
  "ACE inhibitors (blood pressure)", "Beta blockers (blood pressure)",
  "Diuretics / water pills", "Blood thinners (warfarin / Eliquis)",
  "SSRIs / antidepressants", "Thyroid medication", "None",
]

export interface Form1Data {
  height_cm: string; weight_kg: string; age: string; sex: string
  activity_level: string; smoking_status: string; health_goals: string[]
  health_conditions: string[]; medications: string[]; household_size: string
}

const INITIAL: Form1Data = {
  height_cm: "", weight_kg: "", age: "", sex: "", activity_level: "",
  smoking_status: "", health_goals: [], health_conditions: [], medications: [], household_size: "",
}

type Errors = Partial<Record<keyof Form1Data, string>>

// ── Shared styled sub-components ──────────────────────────────────────────────

function Label({ children, htmlFor }: { children: React.ReactNode; htmlFor?: string }) {
  return (
    <label htmlFor={htmlFor} className="block text-sm font-semibold text-emerald-900 mb-1.5">
      {children}
    </label>
  )
}

function FieldError({ message }: { message?: string }) {
  if (!message) return null
  return <p data-error className="mt-1 text-xs font-medium text-red-600 flex items-center gap-1">⚠ {message}</p>
}

const inputClass = "w-full rounded-lg border-2 border-emerald-200 bg-white px-3 py-2.5 text-sm text-emerald-900 placeholder:text-emerald-300 focus:outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-200 transition-all duration-200"

function NumberInput({ id, value, onChange, placeholder, min, max }: {
  id: string; value: string; onChange: (v: string) => void
  placeholder?: string; min?: number; max?: number
}) {
  return (
    <input id={id} type="number" value={value} min={min} max={max}
      placeholder={placeholder} onChange={(e) => onChange(e.target.value)}
      className={inputClass} />
  )
}

function Select({ id, value, onChange, options, placeholder }: {
  id: string; value: string; onChange: (v: string) => void
  options: string[]; placeholder?: string
}) {
  return (
    <select id={id} value={value} onChange={(e) => onChange(e.target.value)}
      className={cn(inputClass, "cursor-pointer", !value && "text-emerald-300")}>
      <option value="" disabled hidden>{placeholder ?? "Select…"}</option>
      {options.map((o) => <option key={o} value={o} className="text-emerald-900">{o}</option>)}
    </select>
  )
}

function CheckboxGroup({ options, selected, onChange }: {
  options: string[]; selected: string[]; onChange: (v: string[]) => void
}) {
  const toggle = (opt: string) =>
    onChange(selected.includes(opt) ? selected.filter((s) => s !== opt) : [...selected, opt])
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
      {options.map((opt) => {
        const checked = selected.includes(opt)
        return (
          <label key={opt} onClick={() => toggle(opt)} className={cn(
            "flex items-center gap-2.5 rounded-lg border-2 px-3 py-2.5 text-sm cursor-pointer transition-all duration-200 select-none",
            checked
              ? "border-emerald-500 bg-emerald-500 text-white font-semibold shadow-md shadow-emerald-200 scale-[1.01]"
              : "border-emerald-200 bg-white text-emerald-800 hover:border-emerald-400 hover:bg-emerald-50"
          )}>
            <span className={cn(
              "flex-shrink-0 w-4 h-4 rounded border-2 flex items-center justify-center transition-all",
              checked ? "border-white bg-white" : "border-emerald-300"
            )}>
              {checked && <span className="text-emerald-600 text-[10px] font-black">✓</span>}
            </span>
            {opt}
          </label>
        )
      })}
    </div>
  )
}

const SECTION_ICONS: Record<string, string> = {
  "Physical Stats": "📏", Lifestyle: "🏃", "Health Goals": "🎯",
  "Health Conditions": "🩺", "Current Medications": "💊",
}

function Section({ title, description, children }: {
  title: string; description?: string; children: React.ReactNode
}) {
  return (
    <section className="bg-white rounded-2xl shadow-sm border border-emerald-100 overflow-hidden">
      <div className="bg-gradient-to-r from-emerald-600 to-teal-500 px-5 py-3">
        <h2 className="text-sm font-bold text-white tracking-wide flex items-center gap-2">
          <span>{SECTION_ICONS[title] ?? "📋"}</span>
          {title}
        </h2>
        {description && <p className="text-xs text-emerald-100 mt-0.5">{description}</p>}
      </div>
      <div className="p-5 space-y-4">{children}</div>
    </section>
  )
}

// ── Validation ────────────────────────────────────────────────────────────────

function validate(data: Form1Data): Errors {
  const errors: Errors = {}
  const h = parseFloat(data.height_cm), w = parseFloat(data.weight_kg)
  const a = parseInt(data.age), hs = parseInt(data.household_size)
  if (!data.height_cm) errors.height_cm = "Required"
  else if (isNaN(h) || h < 50 || h > 300) errors.height_cm = "Enter 50–300 cm"
  if (!data.weight_kg) errors.weight_kg = "Required"
  else if (isNaN(w) || w < 10 || w > 500) errors.weight_kg = "Enter 10–500 kg"
  if (!data.age) errors.age = "Required"
  else if (isNaN(a) || a < 1 || a > 120) errors.age = "Enter 1–120"
  if (!data.sex) errors.sex = "Required"
  if (!data.activity_level) errors.activity_level = "Required"
  if (!data.smoking_status) errors.smoking_status = "Required"
  if (!data.household_size) errors.household_size = "Required"
  else if (isNaN(hs) || hs < 1) errors.household_size = "Must be ≥ 1"
  if (data.health_goals.length === 0) errors.health_goals = "Select at least one goal"
  return errors
}

// ── Main form ─────────────────────────────────────────────────────────────────

export default function Form1({ onSubmit }: { onSubmit?: (data: Form1Data) => void }) {
  const [form, setForm] = useState<Form1Data>(INITIAL)
  const [errors, setErrors] = useState<Errors>({})

  const set = <K extends keyof Form1Data>(key: K) => (val: Form1Data[K]) => {
    setForm((prev) => ({ ...prev, [key]: val }))
    if (errors[key]) setErrors((prev) => ({ ...prev, [key]: undefined }))
  }

  const handleSubmit = (e: React.SyntheticEvent<HTMLFormElement>) => {
    e.preventDefault()
    const errs = validate(form)
    if (Object.keys(errs).length > 0) {
      setErrors(errs)
      e.currentTarget.querySelector<HTMLElement>("[data-error]")?.scrollIntoView({ behavior: "smooth", block: "center" })
      return
    }
    onSubmit?.(form)
  }

  return (
    <form onSubmit={handleSubmit} noValidate className="space-y-5 max-w-2xl mx-auto py-8 px-4">
      <div className="text-center pb-2">
        <p className="text-sm text-emerald-600 font-medium">Step 1 of 2 — Help us personalize your nutrition plan</p>
      </div>

      <Section title="Physical Stats">
        <div className="grid grid-cols-3 gap-3">
          <div>
            <Label htmlFor="height">Height (cm)</Label>
            <NumberInput id="height" value={form.height_cm} onChange={set("height_cm")} placeholder="170" min={50} max={300} />
            <FieldError message={errors.height_cm} />
          </div>
          <div>
            <Label htmlFor="weight">Weight (kg)</Label>
            <NumberInput id="weight" value={form.weight_kg} onChange={set("weight_kg")} placeholder="70" min={10} max={500} />
            <FieldError message={errors.weight_kg} />
          </div>
          <div>
            <Label htmlFor="age">Age</Label>
            <NumberInput id="age" value={form.age} onChange={set("age")} placeholder="35" min={1} max={120} />
            <FieldError message={errors.age} />
          </div>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label htmlFor="sex">Sex</Label>
            <Select id="sex" value={form.sex} onChange={set("sex")} options={SEX_OPTIONS} placeholder="Select sex" />
            <FieldError message={errors.sex} />
          </div>
          <div>
            <Label htmlFor="household">Household Size</Label>
            <NumberInput id="household" value={form.household_size} onChange={set("household_size")} placeholder="3" min={1} />
            <FieldError message={errors.household_size} />
          </div>
        </div>
      </Section>

      <Section title="Lifestyle">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <Label htmlFor="activity">Activity Level</Label>
            <Select id="activity" value={form.activity_level} onChange={set("activity_level")} options={ACTIVITY_OPTIONS} placeholder="Select level" />
            <FieldError message={errors.activity_level} />
          </div>
          <div>
            <Label htmlFor="smoking">Smoking Status</Label>
            <Select id="smoking" value={form.smoking_status} onChange={set("smoking_status")} options={SMOKING_OPTIONS} placeholder="Select status" />
            <FieldError message={errors.smoking_status} />
          </div>
        </div>
      </Section>

      <Section title="Health Goals" description="Select all that apply — we'll prioritize nutrients for each goal.">
        <CheckboxGroup options={HEALTH_GOAL_OPTIONS} selected={form.health_goals} onChange={set("health_goals")} />
        <FieldError message={errors.health_goals} />
      </Section>

      <Section title="Health Conditions" description="Select any that apply to you.">
        <CheckboxGroup options={HEALTH_CONDITION_OPTIONS} selected={form.health_conditions} onChange={set("health_conditions")} />
      </Section>

      <Section title="Current Medications" description="Helps us flag nutrient-drug interactions.">
        <CheckboxGroup options={MEDICATION_OPTIONS} selected={form.medications} onChange={set("medications")} />
      </Section>

      <Button type="submit" size="lg" className="w-full text-base mt-2">
        Next: Grocery Preferences →
      </Button>
    </form>
  )
}
