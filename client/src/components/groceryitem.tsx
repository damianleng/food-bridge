import { useState } from "react"
import { cn } from "@/lib/utils"

export interface GroceryItemData {
  fdc_id: number
  description: string
  brand_name?: string
  food_category?: string
  serving_size?: number
  serving_size_unit?: string
  household_serving?: string
  calories?: number
  protein_g?: number
  fat_g?: number
  carbs_g?: number
  fiber_g?: number
  sodium_mg?: number
  price_usd?: number
  score?: number
  tags?: string[]
}

const TAG_COLORS: Record<string, string> = {
  vegan:         "bg-green-100 text-green-700 border border-green-200",
  vegetarian:    "bg-lime-100 text-lime-700 border border-lime-200",
  halal:         "bg-teal-100 text-teal-700 border border-teal-200",
  kosher:        "bg-blue-100 text-blue-700 border border-blue-200",
  "gluten-free": "bg-yellow-100 text-yellow-700 border border-yellow-200",
  "dairy-free":  "bg-orange-100 text-orange-700 border border-orange-200",
  "low sodium":  "bg-purple-100 text-purple-700 border border-purple-200",
}

function MacroChip({ label, value, unit }: { label: string; value?: number; unit: string }) {
  if (value == null) return null
  return (
    <div className="flex flex-col items-center">
      <span className="text-[9px] font-medium text-emerald-500 uppercase tracking-wide">{label}</span>
      <span className="text-xs font-bold text-emerald-900">{Math.round(value)}<span className="font-normal text-emerald-600">{unit}</span></span>
    </div>
  )
}

export default function GroceryItem({ item }: { item: GroceryItemData }) {
  const [added, setAdded] = useState(false)

  const servingLabel =
    item.household_serving ??
    (item.serving_size && item.serving_size_unit
      ? `${item.serving_size}${item.serving_size_unit}`
      : null)

  return (
    <div className={cn(
      "rounded-2xl border-2 bg-white flex flex-col gap-3 overflow-hidden transition-all duration-200 hover:shadow-lg hover:-translate-y-0.5",
      added
        ? "border-emerald-400 shadow-md shadow-emerald-100"
        : "border-emerald-100 shadow-sm"
    )}>
      {/* Colored top accent bar */}
      <div className={cn(
        "h-1 w-full transition-all duration-300",
        added ? "bg-gradient-to-r from-emerald-500 to-teal-400" : "bg-gradient-to-r from-emerald-200 to-teal-200"
      )} />

      <div className="px-4 pb-4 flex flex-col gap-3">
        {/* Header */}
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1 min-w-0">
            <p className="text-sm font-bold text-emerald-900 leading-snug line-clamp-2">
              {item.description}
            </p>
            {item.brand_name && (
              <p className="text-xs text-emerald-500 mt-0.5 truncate">{item.brand_name}</p>
            )}
          </div>
          {item.price_usd != null && (
            <span className="text-base font-extrabold text-emerald-600 whitespace-nowrap">
              ${item.price_usd.toFixed(2)}
            </span>
          )}
        </div>

        {/* Tags */}
        {item.tags && item.tags.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {item.tags.map((tag) => (
              <span key={tag} className={cn(
                "text-[10px] font-semibold px-2 py-0.5 rounded-full",
                TAG_COLORS[tag.toLowerCase()] ?? "bg-emerald-100 text-emerald-700 border border-emerald-200"
              )}>
                {tag}
              </span>
            ))}
          </div>
        )}

        {/* Macros */}
        <div className="flex justify-between bg-emerald-50 rounded-xl px-3 py-2">
          <MacroChip label="Cal"    value={item.calories}  unit=""   />
          <MacroChip label="Protein" value={item.protein_g} unit="g" />
          <MacroChip label="Carbs"  value={item.carbs_g}   unit="g" />
          <MacroChip label="Fat"    value={item.fat_g}     unit="g" />
          <MacroChip label="Fiber"  value={item.fiber_g}   unit="g" />
          <MacroChip label="Na"     value={item.sodium_mg} unit="mg" />
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between gap-2">
          {servingLabel && (
            <span className="text-[11px] text-emerald-500">per {servingLabel}</span>
          )}
          <button
            onClick={() => setAdded((v) => !v)}
            className={cn(
              "ml-auto h-8 px-4 rounded-lg text-xs font-bold transition-all duration-200 active:scale-95",
              added
                ? "bg-emerald-100 text-emerald-700 border-2 border-emerald-300 hover:bg-red-50 hover:text-red-600 hover:border-red-300"
                : "bg-gradient-to-r from-emerald-600 to-teal-500 text-white shadow-md shadow-emerald-200 hover:shadow-lg hover:shadow-emerald-300 hover:-translate-y-0.5"
            )}
          >
            {added ? "✓ Added" : "+ Add"}
          </button>
        </div>
      </div>
    </div>
  )
}
