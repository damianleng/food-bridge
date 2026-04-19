const SESSION_KEY = "foodbridge_session_id";

export const getSessionId = (): string | null => localStorage.getItem(SESSION_KEY);
export const setSessionId = (id: string) => localStorage.setItem(SESSION_KEY, id);
export const clearSessionId = () => localStorage.removeItem(SESSION_KEY);

const BACKEND_URL = (import.meta.env.VITE_BACKEND_URL as string | undefined) ?? "http://localhost:8000";

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BACKEND_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    let detail = `Server error ${res.status}`;
    try { const b = await res.json(); if (b.detail) detail = b.detail; } catch { /* ignore */ }
    throw new Error(detail);
  }
  return res.json();
}

// ── Step 1: Profile ───────────────────────────────────────────────────────────

export interface ProfileResponse {
  session_id: string;
  profile_id: string;
}

export async function createProfile(data: {
  height_cm: number;
  weight_kg: number;
  age: number;
  sex: string;
  activity_level: string;
  smoking_status: string;
  household_size_adults: number;
  household_size_children: number;
  health_goals: string[];
  health_conditions: string[];
  medications: string[];
}): Promise<ProfileResponse> {
  const result = await post<ProfileResponse>("/profile", {
    ...data,
    session_id: getSessionId() ?? undefined,
  });
  setSessionId(result.session_id);
  return result;
}

// ── Step 2: Preferences ───────────────────────────────────────────────────────

export async function savePreferences(data: {
  profile_id: string;
  weekly_budget_usd: number;
  zip_code: string;
  dietary_preferences: string[];
  allergies: string[];
  cuisine_preferences: string[];
  wic_filter_active: boolean;
}): Promise<void> {
  await post("/preferences", {
    ...data,
    session_id: getSessionId() ?? undefined,
  });
}

// ── Step 3: Food search ───────────────────────────────────────────────────────

export interface FoodResult {
  fdc_id: number;
  name: string;
  data_type: string | null;
  score: number;
  top_nutrients: string[];
}

export async function searchFoods(query: string, profileId?: string): Promise<FoodResult[]> {
  return post<FoodResult[]>("/search", { query, profile_id: profileId ?? null });
}

// ── Step 4: Meal plan ─────────────────────────────────────────────────────────

export async function generateMealPlan(
  profileId: string,
  selectedFoods: { fdc_id: number; name: string }[],
): Promise<string> {
  const res = await post<{ response: string }>("/meal-plan", {
    profile_id: profileId,
    selected_foods: selectedFoods,
  });
  return res.response;
}

// ── Step 5: Grocery list ──────────────────────────────────────────────────────

export async function generateGroceryList(
  profileId: string,
  selectedFoods: { fdc_id: number; name: string }[],
  mealPlanText?: string,
): Promise<string> {
  const res = await post<{ total_estimated_cost_usd: number; grocery_list: unknown }>(
    "/grocery-list",
    { profile_id: profileId, selected_foods: selectedFoods, meal_plan_text: mealPlanText },
  );
  return JSON.stringify(res);
}

// ── Reset ─────────────────────────────────────────────────────────────────────

export async function resetSession(): Promise<void> {
  clearSessionId();
}
