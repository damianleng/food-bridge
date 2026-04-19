# FoodBridge — Codebase Documentation

---

## Architecture Overview

```
Browser (React)
     │
     │  HTTP (fetch)
     ▼
FastAPI Backend (port 8000)
     │
     ├── Direct DB queries (psycopg2) ──► PostgreSQL (port 5433)
     │         user.py, db.py                │
     │                                       ├── USDA FoodData Central (~770K foods)
     │                                       └── User tables (profile, prefs, DV)
     │
     └── LangChain Agent ──────────────► Anthropic Claude Haiku 4.5
               planner.py                    (meal plan generation)
                    │
                    └── DuckDuckGo web search (grocery pricing)
```

Data flows in one direction: user input → profile/preferences stored to DB → food search scored against user's personalized DV → selected foods sent to Claude agent → meal plan JSON returned → grocery list derived + priced → displayed.

---

## Backend

### `db.py` — Database Helpers

Thin wrapper around psycopg2. All functions open a new connection per call (no connection pooling).

```python
fetch_all(sql, params)       → list[dict]   # SELECT multiple rows
fetch_one(sql, params)       → dict | None  # SELECT single row
execute(sql, params)         → None         # INSERT/UPDATE/DELETE
execute_returning(sql, params) → dict       # INSERT ... RETURNING
```

Uses `RealDictCursor` so rows are accessed as `row["column_name"]` not `row[0]`.

Connection config comes from env vars: `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`.

---

### `nutrition.py` — Personalized Nutrition Engine

Pure math — no DB calls. Everything is driven by a `UserProfile` dataclass.

**BMR & TDEE:**
```
BMR = Mifflin-St Jeor equation (differs by sex)
TDEE = BMR × activity_multiplier (1.2 → 1.9)
```

**`calculate_personalized_dv(profile)`** returns 18 nutrient targets:

| Nutrient | Calculation logic |
|----------|------------------|
| `calories_kcal` | TDEE |
| `protein_g` | 0.8–1.2 g/kg body weight (higher for athletes/muscle gain) |
| `fat_g` | 30% of calories |
| `carbohydrates_g` | Remainder after protein + fat |
| `fiber_g` | 14g per 1000 kcal |
| `added_sugars_g` | <10% calories (lower if diabetic) |
| `sodium_mg` | 2300 mg standard; 1500 mg for hypertension |
| `potassium_mg` | 4700 mg standard |
| `calcium_mg` | Age/sex/pregnancy aware |
| `iron_mg` | Higher for menstruating women |
| `vitamin_c_mg` | Higher for smokers (+35 mg) |
| `vitamin_d_iu` | Standard 600 IU |
| `folate_mcg` | Higher during pregnancy |
| `b12_mcg` | Standard 2.4 mcg |
| `magnesium_mg` | Age/sex aware |
| `zinc_mg` | Sex aware |

**`score_food(nutrients, dv)`** — nutrient-density score:
- **Reward**: protein, fiber, potassium, calcium, iron, vitamins — weighted by importance, each capped at 100% DV contribution
- **Penalty**: calories, saturated fat, sodium, added sugars — subtracts excess
- Returns raw float; `user.py` scales this 0–100 for display

**`NUTRIENT_ID_MAP`** maps USDA nutrient IDs to DV keys (e.g., `1003 → "protein_g"`, `1093 → "sodium_mg"`).

---

### `user.py` — Business Logic

#### Profile Creation — `create_profile()`

1. `INSERT INTO user_profile` (demographics)
2. `INSERT INTO user_health_goal` for each goal
3. `INSERT INTO user_health_condition` for each condition
4. `INSERT INTO user_medication` for each medication
5. Calls `nutrition.calculate_personalized_dv()` → `INSERT INTO user_calculated_dv`

Returns `profile_id` (UUID string).

#### Preferences — `save_preferences()`

Upserts `user_grocery_preference` (budget, zip, WIC flag) then does DELETE + INSERT for dietary_preferences, allergies, and cuisine_preferences to keep them in sync.

#### Food Search — `search_foods(query, profile_id)`

```
1. SELECT food WHERE description ILIKE '%query%' LIMIT 100
2. Filter out allergen matches (user_allergy)
3. Filter out dietary restriction conflicts (17 rules, e.g. vegetarian excludes "chicken", "beef"...)
4. For remaining candidates, batch-fetch food_nutrient in one query
5. Load user's personalized DV from user_calculated_dv
6. Score each food via nutrition.score_food()
7. Apply cuisine boost (+15 pts if food name matches cuisine keywords)
8. Sort by score, return top 20
```

**`_CUISINE_KEYWORDS`** maps cuisine names to food keywords:
- `"Asian"` → tofu, bok choy, rice, soy, edamame, miso...
- `"Mexican"` → black bean, corn, avocado, jalapeño, tortilla...
- `"Mediterranean"` → olive, hummus, chickpea, feta, quinoa, lentil...

**`_DIETARY_FILTER_RULES`** — 17 diet types with excluded keywords. Vegetarian excludes `["beef", "pork", "chicken", "turkey", "fish", "seafood", "meat", "bacon", "ham", "sausage", "salami", "pepperoni"]`.

#### Grocery List — `derive_grocery_list(selected_foods)`

Categorizes each food by keyword matching into 7 categories, looks up serving size from `branded_food` table (falls back to category default), assigns default quantity per category:

| Category | Default serving | Default qty |
|----------|----------------|-------------|
| Meat & Seafood | 450g | 3 |
| Dairy & Eggs | 500g | 2 |
| Produce | 300g | 2 |
| Grains & Legumes | 500g | 1 |
| Fats & Oils | 250g | 1 |
| Nuts & Seeds | 200g | 1 |
| Other | 300g | 2 |

---

### `planner.py` — AI Agents

#### Meal Plan Agent

Uses **LangChain ReAct agent** with Claude Haiku 4.5 and `SQLDatabaseToolkit` (4 SQL tools: list tables, schema, query checker, query executor).

The agent has read-only access to these tables:
`food`, `food_category`, `food_nutrient`, `nutrient`, `branded_food`, `user_profile`, `user_calculated_dv`, `user_grocery_preference`, `user_dietary_preference`, `user_allergy`, `user_medication`, `user_health_condition`

**Hard constraints in system prompt:**

| Condition | Avoid | Substitute with |
|-----------|-------|-----------------|
| Diabetes/insulin | sugar, syrup, white rice, candy, juice | oats, lentils, brown rice, berries, leafy greens |
| Hypertension | >600mg sodium foods, processed meats | fresh produce, whole grains, lean proteins |
| Warfarin/blood thinners | large amounts of kale, spinach (high vitamin K) | broccoli, carrots, peas |
| Statins | saturated fat, fried foods, full-fat dairy | oats, beans, olive oil, fish |

**Output format (JSON):**
```json
{
  "days": [
    {"day": "Day 1", "meals": [
      {"name": "Breakfast: Oats + Yogurt"},
      {"name": "Lunch: Chicken + Broccoli"},
      {"name": "Dinner: Salmon + Rice"}
    ]}
  ],
  "nutrient_coverage": {"calories_kcal": 95, "protein_g": 110, "fiber_g": 88},
  "suggested_swaps": [
    {"original": "Candy Bar", "replacement": "Mixed Berries", "reason": "User takes insulin"}
  ]
}
```

Recursion limit: 15 steps (prevents runaway LLM loops).

#### Grocery Pricing — `get_grocery_prices(grocery_list, zip_code)`

Single DuckDuckGo search + single Claude LLM call (no agent loop):

```
1. Extract short names from USDA descriptions
   - "WHOLE FOODS MARKET, ASIAN COOKING SEASONING" → "ASIAN COOKING SEASONING"
   - Known brands (_KNOWN_BRANDS set) are stripped from prefix
2. One DuckDuckGo search: "grocery store prices {items} near zip {zip} 2025"
3. Pass search results + full item list to Claude
4. Claude returns JSON: [{name, price_usd, unit, store}, ...] + total
5. Regex extracts JSON from response
```

---

### `api.py` — REST Endpoints

All endpoints use Pydantic models for validation. CORS is open (`allow_origins=["*"]`).

#### `POST /profile`
Accepts `ProfileRequest` → calls `user.create_profile()` → returns `{session_id, profile_id}`.

#### `POST /preferences`
Accepts `PreferencesRequest` → calls `user.save_preferences()` → returns `{status: "ok"}`.

#### `POST /search`
Accepts `{query, profile_id}` → calls `user.search_foods()` → returns list of `FoodResult`.

#### `POST /meal-plan`
Accepts `{profile_id, selected_foods}` → calls `planner.generate_meal_plan()` (blocking, runs Claude agent) → returns `{response: "<JSON string>"}`.

#### `POST /grocery-list`
```
1. user.derive_grocery_list(selected_foods) → categorized list
2. Fetch user's zip_code from user_grocery_preference
3. Run planner.get_grocery_prices(grocery_list, zip_code) in thread executor
   (needed because DuckDuckGo search is sync, endpoint is async)
4. Fuzzy match agent prices back to grocery items by word overlap
5. Return {total_estimated_cost_usd, grocery_list: {category: [items]}}
```

---

## Frontend

### `store/app.ts` — Zustand Store

Global state with selective localStorage persistence (via `partialize`):

**Persisted to localStorage:** `screen`, `onboardingStep`, `profileId`, `profile`, `preferences`

**Not persisted** (reset on refresh): `selectedFoods`, `mealPlanResponse`, `groceryResponse`

Key types:
- `Profile` — health demographic data
- `Preferences` — budget, zip, diet, allergies, cuisines, WIC
- `FoodItem` — `{fdc_id, name, data_type, score, top_nutrients}`

### `lib/api.ts` — API Client

All functions use `fetch` with `BASE_URL` from `import.meta.env.VITE_BACKEND_URL` (default `http://localhost:8000`).

```typescript
createProfile(data)              → POST /profile
savePreferences(data)            → POST /preferences
searchFoods(query, profileId)    → POST /search
generateMealPlan(profileId, foods) → POST /meal-plan
generateGroceryList(profileId, foods) → POST /grocery-list
resetSession()                   → POST /reset
```

### Screens

| Screen | Step | Key logic |
|--------|------|-----------|
| `Onboarding.tsx` | 1/5 | 6-step form, converts imperial/metric, validates ranges, calls `createProfile` |
| `Preferences.tsx` | 2/5 | Budget/zip/diet/allergy/cuisine multi-select, calls `savePreferences` |
| `FoodSearch.tsx` | 3/5 | Search + toggle food selection, score badges, selected chips, min 3 foods required |
| `MealPlan.tsx` | 4/5 | Parses meal plan JSON, day tabs, meal cards, nutrient coverage bars, suggested swaps |
| `GroceryList.tsx` | 5/5 | Groups items by category, shows `qty × unit_price = subtotal`, budget progress bar |

---

## Database Schema

### USDA Tables (read-only)

| Table | Key columns |
|-------|-------------|
| `food` | `fdc_id`, `description`, `data_type`, `food_category_id` |
| `food_nutrient` | `fdc_id`, `nutrient_id`, `amount` (per 100g) |
| `nutrient` | `id`, `name`, `unit_name` |
| `branded_food` | `fdc_id`, `brand_name`, `serving_size`, `serving_size_unit` |
| `food_category` | `id`, `description` |

### User Tables (application-owned)

| Table | Primary key | Purpose |
|-------|-------------|---------|
| `user_profile` | `profile_id` (UUID) | Core demographics |
| `user_health_goal` | `id` | Goals: weight_loss, muscle_gain, etc. |
| `user_health_condition` | `id` | Conditions: hypertension, type_2_diabetes, etc. |
| `user_medication` | `id` | Medication names |
| `user_calculated_dv` | `id` | 18 personalized nutrient targets |
| `user_grocery_preference` | `id` (unique profile_id) | Budget, zip, WIC flag |
| `user_dietary_preference` | `id` | vegetarian, vegan, keto, etc. |
| `user_allergy` | `id` | peanut, shellfish, dairy, etc. |
| `user_cuisine_preference` | `id` | Mediterranean, Asian, Mexican, etc. |

---

## Key Design Decisions

**Why Claude agent for meal planning but not grocery pricing?**
Meal planning requires multi-step reasoning (check allergies → check medications → find substitutes → build 7 days). Grocery pricing is a lookup that maps well to one search + one extraction call — an agent loop would be slower and more expensive.

**Why USDA FoodData Central?**
It's the most comprehensive free nutrition database (~770K foods, 150+ nutrients). The `food_nutrient` table stores per-100g amounts, making nutritional comparisons straightforward.

**Why personalized daily values instead of standard RDAs?**
Standard RDAs are averages. A 300-lb man training daily has very different protein needs than a sedentary 110-lb woman. Scoring foods against personalized DVs makes search results meaningfully ranked.

**Why fuzzy word matching for price assignment?**
The AI returns short names like `"Chicken Breast"` but USDA descriptions are long like `"Chicken, broilers or fryers, breast, meat only, cooked, roasted"`. Word-overlap matching bridges this gap without requiring exact strings.
