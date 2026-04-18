const SESSION_KEY = "foodbridge_session_id";

export const getSessionId = (): string | null => localStorage.getItem(SESSION_KEY);
export const setSessionId = (id: string) => localStorage.setItem(SESSION_KEY, id);
export const clearSessionId = () => localStorage.removeItem(SESSION_KEY);

export interface ChatResponse {
  session_id: string;
  response: string;
}

// ── Mock responses per screen ─────────────────────────────────────────────────

const MOCK_FOODS = JSON.stringify([
  { fdc_id: 171477, name: "Chicken Breast, Raw", data_type: "foundation_food", score: 8.4, top_nutrients: ["protein_g", "vitamin_b6", "phosphorus"] },
  { fdc_id: 168917, name: "Whole Milk", data_type: "sr_legacy_food", score: 6.1, top_nutrients: ["calcium_mg", "vitamin_d_iu", "protein_g"] },
  { fdc_id: 170379, name: "Brown Rice, Cooked", data_type: "sr_legacy_food", score: 5.3, top_nutrients: ["fiber_g", "magnesium_mg", "carbohydrates_g"] },
  { fdc_id: 169967, name: "Broccoli, Raw", data_type: "foundation_food", score: 7.9, top_nutrients: ["vitamin_c_mg", "vitamin_k", "fiber_g"] },
  { fdc_id: 171705, name: "Salmon, Atlantic, Farmed", data_type: "sr_legacy_food", score: 8.8, top_nutrients: ["omega_3", "protein_g", "vitamin_d_iu"] },
  { fdc_id: 168462, name: "Oats, Rolled, Dry", data_type: "foundation_food", score: 6.7, top_nutrients: ["fiber_g", "iron_mg", "magnesium_mg"] },
  { fdc_id: 170556, name: "Greek Yogurt, Plain", data_type: "branded_food", score: 7.2, top_nutrients: ["protein_g", "calcium_mg", "probiotics"] },
  { fdc_id: 171287, name: "Lentils, Cooked", data_type: "sr_legacy_food", score: 7.6, top_nutrients: ["fiber_g", "folate_mcg", "iron_mg"] },
  { fdc_id: 171018, name: "Sweet Potato, Baked", data_type: "foundation_food", score: 6.9, top_nutrients: ["vitamin_a", "potassium_mg", "fiber_g"] },
  { fdc_id: 171304, name: "Black Beans, Canned", data_type: "branded_food", score: 6.4, top_nutrients: ["fiber_g", "protein_g", "folate_mcg"] },
]);

const MOCK_MEAL_PLAN = JSON.stringify({
  nutrition_coverage_pct: {
    calories_kcal: 98, protein_g: 112, fat_g: 88, fiber_g: 95,
    calcium_mg: 76, iron_mg: 82, vitamin_c_mg: 104, vitamin_d_iu: 61,
    sodium_mg: 72, potassium_mg: 89,
  },
  days: [
    { day: "Day 1", meals: [{ name: "🥣 Oats + Greek Yogurt" }, { name: "🥗 Chicken Breast + Broccoli" }, { name: "🐟 Salmon + Brown Rice" }] },
    { day: "Day 2", meals: [{ name: "🥚 Eggs + Sweet Potato" }, { name: "🫘 Lentil Soup" }, { name: "🍗 Chicken + Black Beans" }] },
    { day: "Day 3", meals: [{ name: "🥣 Oats + Berries" }, { name: "🐟 Salmon Salad" }, { name: "🥗 Broccoli + Brown Rice" }] },
    { day: "Day 4", meals: [{ name: "🥛 Greek Yogurt Bowl" }, { name: "🫘 Black Bean Tacos" }, { name: "🍗 Chicken Stir Fry" }] },
    { day: "Day 5", meals: [{ name: "🥣 Overnight Oats" }, { name: "🥗 Lentil Salad" }, { name: "🐟 Baked Salmon" }] },
    { day: "Day 6", meals: [{ name: "🍠 Sweet Potato Hash" }, { name: "🍗 Grilled Chicken" }, { name: "🫘 Lentil + Rice Bowl" }] },
    { day: "Day 7", meals: [{ name: "🥣 Oats + Yogurt" }, { name: "🥗 Broccoli Soup" }, { name: "🐟 Salmon + Sweet Potato" }] },
  ],
  suggested_swaps: [
    { food: "Fortified Almond Milk", reason: "vitamin_d_iu only at 61% — boosts vitamin D" },
    { food: "Spinach", reason: "iron_mg at 82% — excellent non-heme iron source" },
  ],
});

const MOCK_GROCERY = JSON.stringify({
  total_estimated_cost_usd: 87.42,
  grocery_list: {
    "Meat & Seafood": [
      { description: "Chicken Breast, Raw", brand: "Nature's Best", quantity_needed: 3, estimated_unit_price_usd: 6.49, price_source: "open_prices" },
      { description: "Salmon, Atlantic, Farmed", brand: "Wild Catch Co.", quantity_needed: 2, estimated_unit_price_usd: 8.99, price_source: "open_prices" },
    ],
    "Dairy & Eggs": [
      { description: "Greek Yogurt, Plain", brand: "Chobani", quantity_needed: 4, estimated_unit_price_usd: 2.79, price_source: "open_prices" },
      { description: "Whole Milk", brand: "Organic Valley", quantity_needed: 1, estimated_unit_price_usd: 4.29, price_source: "category_estimate" },
    ],
    "Produce": [
      { description: "Broccoli, Raw", brand: null, quantity_needed: 3, estimated_unit_price_usd: 1.99, price_source: "category_estimate" },
      { description: "Sweet Potato", brand: null, quantity_needed: 4, estimated_unit_price_usd: 0.89, price_source: "category_estimate" },
    ],
    "Grains & Legumes": [
      { description: "Oats, Rolled", brand: "Bob's Red Mill", quantity_needed: 1, estimated_unit_price_usd: 4.49, price_source: "open_prices" },
      { description: "Brown Rice", brand: "Lundberg", quantity_needed: 1, estimated_unit_price_usd: 3.99, price_source: "open_prices" },
      { description: "Lentils, Green", brand: "365 Whole Foods", quantity_needed: 1, estimated_unit_price_usd: 2.49, price_source: "category_estimate" },
      { description: "Black Beans, Canned", brand: "Bush's Best", quantity_needed: 2, estimated_unit_price_usd: 1.29, price_source: "open_prices" },
    ],
  },
});

function mockResponse(message: string): string {
  const m = message.toLowerCase();
  if (m.includes("grocery list")) return MOCK_GROCERY;
  if (m.includes("search for foods") || m.includes("score them")) return MOCK_FOODS;
  if (m.includes("7-day meal plan") || m.includes("meal plan")) return MOCK_MEAL_PLAN;
  return "Got it! Moving to the next step.";
}

// ── Public API ────────────────────────────────────────────────────────────────

export async function chat(message: string): Promise<ChatResponse> {
  // Simulate network delay
  await new Promise((r) => setTimeout(r, 600));
  return { session_id: "mock-session", response: mockResponse(message) };
}

export async function resetSession(): Promise<void> {
  clearSessionId();
}