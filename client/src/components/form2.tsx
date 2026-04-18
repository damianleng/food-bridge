import { useState } from "react"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

const DIETARY_PREF_OPTIONS = [
  "Vegetarian", "Vegan", "Halal", "Kosher", "Gluten-free", "Dairy-free",
  "Low sodium", "Low sugar / diabetic-friendly", "Low carb / keto",
  "High protein", "Whole foods / minimally processed", "No restrictions",
]

const ALLERGY_OPTIONS = [
  "Peanuts", "Tree nuts (almonds, cashews, walnuts…)", "Milk / Dairy",
  "Eggs", "Wheat / Gluten", "Soy", "Fish",
  "Shellfish (shrimp, crab, lobster…)", "Sesame", "None",
]

const CUISINE_OPTIONS = [
  "American / Southern", "Latin American", "Mexican / Tex-Mex", "Caribbean",
  "West African", "East African", "Mediterranean", "Middle Eastern",
  "South Asian (Indian, Pakistani…)", "Southeast Asian (Vietnamese, Thai…)",
  "East Asian (Chinese, Korean, Japanese…)", "Eastern European", "No preference",
]

export interface Form2Data {
  weekly_budget_usd: string
  household_size: string
  zip_code: string
  dietary_preferences: string[]
  allergies: string[]
  cuisine_preferences: string[]
}

const INITIAL: Form2Data = {
  weekly_budget_usd: "", household_size: "", zip_code: "",
  dietary_preferences: [], allergies: [], cuisine_preferences: [],
}

type Errors = Partial<Record<keyof Form2Data, string>>

// ── Shared sub-components ─────────────────────────────────────────────────────

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
  "Budget & Location": "💰",
  "Dietary Preferences": "🥗",
  "Food Allergies & Intolerances": "⚠️",
  "Cuisine Preferences": "🌍",
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

function validate(data: Form2Data): Errors {
  const errors: Errors = {}
  const budget = parseFloat(data.weekly_budget_usd)
  const hs = parseInt(data.household_size)
  if (!data.weekly_budget_usd) errors.weekly_budget_usd = "Required"
  else if (isNaN(budget) || budget <= 0) errors.weekly_budget_usd = "Enter a positive dollar amount"
  if (!data.household_size) errors.household_size = "Required"
  else if (isNaN(hs) || hs < 1) errors.household_size = "Must be at least 1"
  if (!data.zip_code) errors.zip_code = "Required"
  else if (!/^\d{5}(-\d{4})?$/.test(data.zip_code.trim())) errors.zip_code = "Enter a valid US ZIP code"
  return errors
}

// ── Main form ─────────────────────────────────────────────────────────────────

export default function Form2({ onSubmit }: { onSubmit?: (data: Form2Data) => void }) {
  const [form, setForm] = useState<Form2Data>(INITIAL)
  const [errors, setErrors] = useState<Errors>({})

  const set = <K extends keyof Form2Data>(key: K) => (val: Form2Data[K]) => {
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
        <p className="text-sm text-emerald-600 font-medium">Step 2 of 2 — Set your budget and food preferences</p>
      </div>

      <Section title="Budget & Location">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div>
            <Label htmlFor="budget">Weekly Budget (USD)</Label>
            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-sm text-emerald-400 font-semibold">$</span>
              <input
                id="budget" type="number" min={1} step={0.01}
                value={form.weekly_budget_usd} placeholder="150"
                onChange={(e) => set("weekly_budget_usd")(e.target.value)}
                className={cn(inputClass, "pl-7")}
              />
            </div>
            <FieldError message={errors.weekly_budget_usd} />
          </div>
          <div>
            <Label htmlFor="household">Household Size</Label>
            <input
              id="household" type="number" min={1}
              value={form.household_size} placeholder="3"
              onChange={(e) => set("household_size")(e.target.value)}
              className={inputClass}
            />
            <FieldError message={errors.household_size} />
          </div>
          <div>
            <Label htmlFor="zip">ZIP Code</Label>
            <input
              id="zip" type="text"
              value={form.zip_code} placeholder="60629"
              onChange={(e) => set("zip_code")(e.target.value)}
              className={inputClass}
            />
            <FieldError message={errors.zip_code} />
          </div>
        </div>
      </Section>

      <Section title="Dietary Preferences" description="Select all that apply.">
        <CheckboxGroup options={DIETARY_PREF_OPTIONS} selected={form.dietary_preferences} onChange={set("dietary_preferences")} />
      </Section>

      <Section title="Food Allergies & Intolerances" description="Foods containing these ingredients will be excluded.">
        <CheckboxGroup options={ALLERGY_OPTIONS} selected={form.allergies} onChange={set("allergies")} />
      </Section>

      <Section title="Cuisine Preferences" description="We'll boost culturally relevant options in your recommendations.">
        <CheckboxGroup options={CUISINE_OPTIONS} selected={form.cuisine_preferences} onChange={set("cuisine_preferences")} />
      </Section>

      <Button type="submit" size="lg" className="w-full text-base mt-2">
        Find My Recommendations →
      </Button>
    </form>
  )
}
