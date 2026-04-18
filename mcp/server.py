"""
FoodBridge MCP Server
Tools: capture_user_profile, calculate_personalized_dv, capture_preferences,
       query_fooddata_central, score_foods_by_nutrient_density,
       check_budget_constraint, optimize_meal_plan, generate_grocery_list
"""

import asyncio
import json
from mcp.server.fastmcp import FastMCP

from db import fetchall, fetchone, execute, execute_returning
from grocery_api import get_grocery_prices_bulk
from nutrition import (
    UserProfile,
    calculate_personalized_dv as _calc_dv,
    score_food,
    NUTRIENT_ID_MAP,
)

mcp = FastMCP("FoodBridge")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_dv(profile_id: str) -> dict:
    row = fetchone(
        "SELECT * FROM user_calculated_dv WHERE profile_id = %s ORDER BY calculated_at DESC LIMIT 1",
        (profile_id,),
    )
    if not row:
        raise ValueError(f"No calculated DV found for profile {profile_id}. Run calculate_personalized_dv first.")
    return {k: float(v) for k, v in row.items() if k not in ("id", "profile_id", "calculated_at") and v is not None}


def _get_user_filters(profile_id: str) -> tuple[list[str], list[str]]:
    """Return (allergies, dietary_preferences) for a profile."""
    allergies = [
        r["allergen"] for r in fetchall(
            "SELECT allergen FROM user_allergy WHERE profile_id = %s", (profile_id,)
        )
    ]
    prefs = [
        r["preference"] for r in fetchall(
            "SELECT preference FROM user_dietary_preference WHERE profile_id = %s", (profile_id,)
        )
    ]
    return allergies, prefs


# ── Dietary filter rules ──────────────────────────────────────────────────────
# Maps preference name → keywords that disqualify a food via category or ingredients.
# "max_sodium_mg" and "max_carb_g" are nutrient hard-caps per 100g.

DIETARY_FILTER_RULES: dict[str, dict] = {
    "vegetarian": {
        "bad_categories": ["meat", "poultry", "seafood", "fish", "beef", "pork", "chicken", "lamb", "turkey"],
        "bad_ingredients": ["beef", "pork", "chicken", "turkey", "lamb", "duck", "veal", "bison",
                            "venison", "fish", "shrimp", "lobster", "crab", "gelatin", "lard", "tallow"],
    },
    "vegan": {
        "bad_categories": ["meat", "poultry", "seafood", "fish", "beef", "pork", "chicken",
                           "dairy", "cheese", "milk", "egg"],
        "bad_ingredients": ["beef", "pork", "chicken", "turkey", "lamb", "fish", "shrimp",
                            "gelatin", "lard", "tallow", "milk", "cheese", "butter", "cream",
                            "whey", "casein", "lactose", "yogurt", "ghee", "egg", "honey",
                            "albumin", "collagen"],
    },
    "gluten_free": {
        "bad_categories": [],
        "bad_ingredients": ["wheat", "barley", "rye", "malt", "triticale", "spelt",
                            "kamut", "farro", "semolina", "durum", "bulgur", "couscous"],
    },
    "dairy_free": {
        "bad_categories": ["dairy", "cheese", "milk"],
        "bad_ingredients": ["milk", "cheese", "butter", "cream", "whey", "casein",
                            "lactose", "yogurt", "ghee", "kefir", "curds"],
    },
    "nut_free": {
        "bad_categories": [],
        "bad_ingredients": ["peanut", "almond", "cashew", "walnut", "pecan", "hazelnut",
                            "pistachio", "macadamia", "brazil nut", "pine nut", "chestnut"],
    },
    "low_sodium": {
        "bad_categories": [],
        "bad_ingredients": [],
        "max_sodium_mg": 140,      # FDA definition of "low sodium" per serving (~100g)
    },
    "low_carb": {
        "bad_categories": [],
        "bad_ingredients": [],
        "max_carb_g": 10,          # <10g net carbs per 100g
    },
    "keto": {
        "bad_categories": ["grain", "bread", "cereal", "pasta", "rice", "sugar", "candy"],
        "bad_ingredients": ["sugar", "corn syrup", "honey", "maple syrup", "flour",
                            "starch", "dextrose", "maltodextrin"],
        "max_carb_g": 5,
    },
    "halal": {
        "bad_categories": [],
        "bad_ingredients": ["pork", "lard", "gelatin", "alcohol", "wine", "beer"],
    },
    "kosher": {
        "bad_categories": [],
        "bad_ingredients": ["pork", "shellfish", "shrimp", "lobster", "crab", "lard"],
    },
}


def _filter_foods(
    scored_foods: list[dict],
    branded_map: dict[int, dict],
    nutrient_map: dict[int, dict[str, float]],
    allergies: list[str],
    dietary_prefs: list[str],
) -> tuple[list[dict], list[dict]]:
    """
    Filter a scored food list against allergies and dietary preferences.

    Returns (safe_foods, rejected_foods) where each rejected entry carries a reason.
    Checks (in order):
      1. Allergens against food description + branded ingredients
      2. Dietary preference bad_categories against branded_food_category
      3. Dietary preference bad_ingredients against branded ingredients
      4. Nutrient hard-caps (low_sodium max_sodium_mg, low_carb/keto max_carb_g)
    """
    safe: list[dict] = []
    rejected: list[dict] = []

    for food in scored_foods:
        fid = food["fdc_id"]
        desc = food["description"].lower()
        branded = branded_map.get(fid, {})
        ingredients = (branded.get("ingredients") or "").lower()
        category = (branded.get("branded_food_category") or "").lower()
        nutrients = nutrient_map.get(fid, {})

        reject_reason: str | None = None

        # 1. Allergen check — description + ingredients
        for allergen in allergies:
            kw = allergen.lower()
            if kw in desc or kw in ingredients:
                reject_reason = f"allergen: {allergen}"
                break

        if reject_reason:
            rejected.append({**food, "rejected_reason": reject_reason})
            continue

        # 2 & 3. Dietary preference checks
        for pref in dietary_prefs:
            rules = DIETARY_FILTER_RULES.get(pref.lower(), {})

            for bad_cat in rules.get("bad_categories", []):
                if bad_cat in category or bad_cat in desc:
                    reject_reason = f"dietary_pref '{pref}': category contains '{bad_cat}'"
                    break

            if reject_reason:
                break

            for bad_ing in rules.get("bad_ingredients", []):
                if bad_ing in ingredients or bad_ing in desc:
                    reject_reason = f"dietary_pref '{pref}': ingredient contains '{bad_ing}'"
                    break

            if reject_reason:
                break

            # 4. Nutrient hard-caps
            max_sodium = rules.get("max_sodium_mg")
            if max_sodium and nutrients.get("sodium_mg", 0) > max_sodium:
                reject_reason = f"dietary_pref '{pref}': sodium {nutrients['sodium_mg']:.0f}mg > {max_sodium}mg per 100g"
                break

            max_carb = rules.get("max_carb_g")
            if max_carb and nutrients.get("carbohydrates_g", 0) > max_carb:
                reject_reason = f"dietary_pref '{pref}': carbs {nutrients['carbohydrates_g']:.1f}g > {max_carb}g per 100g"
                break

        if reject_reason:
            rejected.append({**food, "rejected_reason": reject_reason})
        else:
            safe.append(food)

    return safe, rejected


# ── Tool 1: capture_user_profile ──────────────────────────────────────────────

@mcp.tool()
def capture_user_profile(
    height_cm: float,
    weight_kg: float,
    age: int,
    sex: str,
    activity_level: str,
    smoking_status: str = "non_smoker",
    pregnancy_status: str = "not_pregnant",
    household_size_adults: int = 1,
    household_size_children: int = 0,
    health_goals: list[str] = [],
    health_conditions: list[str] = [],
    medications: list[dict] = [],
) -> dict:
    """
    Capture and persist a user's health profile.

    Args:
        height_cm: Height in centimetres
        weight_kg: Weight in kilograms
        age: Age in years
        sex: "male" or "female"
        activity_level: One of sedentary | lightly_active | moderately_active | very_active | extra_active
        smoking_status: "smoker" | "non_smoker" | "former_smoker"
        pregnancy_status: "not_pregnant" | "pregnant" | "lactating"
        household_size_adults: Number of adults in household
        household_size_children: Number of children in household
        health_goals: List of goals e.g. ["weight_loss", "muscle_gain"]
        health_conditions: List of conditions e.g. ["hypertension", "diabetes"]
        medications: List of dicts with keys: medication_name, rxcui (optional), drug_class (optional)

    Returns:
        dict with profile_id (UUID string) to pass to all subsequent tools
    """
    row = execute_returning(
        """
        INSERT INTO user_profile (
            height_cm, weight_kg, age, sex, activity_level,
            smoking_status, pregnancy_status,
            household_size_adults, household_size_children
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        RETURNING profile_id
        """,
        (
            height_cm, weight_kg, age, sex, activity_level,
            smoking_status, pregnancy_status,
            household_size_adults, household_size_children,
        ),
    )
    profile_id = str(row["profile_id"])

    for goal in health_goals:
        execute(
            "INSERT INTO user_health_goal (profile_id, goal) VALUES (%s, %s)",
            (profile_id, goal),
        )
    for condition in health_conditions:
        execute(
            "INSERT INTO user_health_condition (profile_id, condition_name) VALUES (%s, %s)",
            (profile_id, condition),
        )
    for med in medications:
        execute(
            "INSERT INTO user_medication (profile_id, medication_name, rxcui, drug_class) VALUES (%s,%s,%s,%s)",
            (profile_id, med.get("medication_name"), med.get("rxcui"), med.get("drug_class")),
        )

    return {
        "profile_id": profile_id,
        "message": "Profile created. Use this profile_id in all subsequent tools.",
    }


# ── Tool 2: calculate_personalized_dv ────────────────────────────────────────

@mcp.tool()
def calculate_personalized_dv(profile_id: str) -> dict:
    """
    Calculate and store personalised daily nutritional values for a user.

    Uses Mifflin-St Jeor for BMR, applies activity multiplier for TDEE,
    then derives macros and micros adjusted for health goals, conditions,
    pregnancy status, and smoking status.

    Args:
        profile_id: UUID returned by capture_user_profile

    Returns:
        dict of personalised daily values (calories, macros, key micros)
    """
    profile_row = fetchone("SELECT * FROM user_profile WHERE profile_id = %s", (profile_id,))
    if not profile_row:
        raise ValueError(f"Profile {profile_id} not found.")

    goals = [r["goal"] for r in fetchall("SELECT goal FROM user_health_goal WHERE profile_id = %s", (profile_id,))]
    conditions = [r["condition_name"] for r in fetchall("SELECT condition_name FROM user_health_condition WHERE profile_id = %s", (profile_id,))]

    profile = UserProfile(
        height_cm=float(profile_row["height_cm"]),
        weight_kg=float(profile_row["weight_kg"]),
        age=int(profile_row["age"]),
        sex=profile_row["sex"],
        activity_level=profile_row["activity_level"],
        smoking_status=profile_row["smoking_status"],
        pregnancy_status=profile_row["pregnancy_status"],
        health_goals=goals,
        health_conditions=conditions,
    )

    dv = _calc_dv(profile)

    execute(
        """
        INSERT INTO user_calculated_dv (
            profile_id, calories_kcal, protein_g, fat_g, saturated_fat_g,
            carbohydrates_g, fiber_g, added_sugars_g, sodium_mg, potassium_mg,
            calcium_mg, iron_mg, vitamin_c_mg, vitamin_d_iu, folate_mcg,
            b12_mcg, magnesium_mg, zinc_mg
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        (
            profile_id,
            dv["calories_kcal"], dv["protein_g"], dv["fat_g"], dv["saturated_fat_g"],
            dv["carbohydrates_g"], dv["fiber_g"], dv["added_sugars_g"], dv["sodium_mg"],
            dv["potassium_mg"], dv["calcium_mg"], dv["iron_mg"], dv["vitamin_c_mg"],
            dv["vitamin_d_iu"], dv["folate_mcg"], dv["b12_mcg"], dv["magnesium_mg"],
            dv["zinc_mg"],
        ),
    )

    return {"profile_id": profile_id, "daily_values": dv}


# ── Tool 3: capture_preferences ──────────────────────────────────────────────

@mcp.tool()
def capture_preferences(
    profile_id: str,
    weekly_budget_usd: float,
    zip_code: str,
    dietary_preferences: list[str] = [],
    allergies: list[str] = [],
    cuisine_preferences: list[str] = [],
    wic_filter_active: str = "N",
) -> dict:
    """
    Capture and persist a user's grocery and dietary preferences.

    Args:
        profile_id: UUID returned by capture_user_profile
        weekly_budget_usd: Weekly grocery budget in USD
        zip_code: User's zip code (used for local store lookup)
        dietary_preferences: e.g. ["vegetarian", "gluten_free", "low_sodium"]
        allergies: e.g. ["peanuts", "shellfish", "dairy"]
        cuisine_preferences: e.g. ["Mexican", "Mediterranean", "Asian"]
        wic_filter_active: "Y" to filter to WIC-eligible items only, "N" otherwise

    Returns:
        Confirmation dict
    """
    execute(
        """
        INSERT INTO user_grocery_preference (profile_id, weekly_budget_usd, zip_code, wic_filter_active)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (profile_id) DO UPDATE
            SET weekly_budget_usd = EXCLUDED.weekly_budget_usd,
                zip_code          = EXCLUDED.zip_code,
                wic_filter_active = EXCLUDED.wic_filter_active,
                updated_at        = NOW()
        """,
        (profile_id, weekly_budget_usd, zip_code, wic_filter_active),
    )

    execute("DELETE FROM user_dietary_preference WHERE profile_id = %s", (profile_id,))
    for pref in dietary_preferences:
        execute("INSERT INTO user_dietary_preference (profile_id, preference) VALUES (%s,%s)", (profile_id, pref))

    execute("DELETE FROM user_allergy WHERE profile_id = %s", (profile_id,))
    for allergen in allergies:
        execute("INSERT INTO user_allergy (profile_id, allergen) VALUES (%s,%s)", (profile_id, allergen))

    execute("DELETE FROM user_cuisine_preference WHERE profile_id = %s", (profile_id,))
    for cuisine in cuisine_preferences:
        execute("INSERT INTO user_cuisine_preference (profile_id, cuisine) VALUES (%s,%s)", (profile_id, cuisine))

    return {
        "profile_id": profile_id,
        "weekly_budget_usd": weekly_budget_usd,
        "zip_code": zip_code,
        "dietary_preferences": dietary_preferences,
        "allergies": allergies,
        "cuisine_preferences": cuisine_preferences,
        "wic_filter_active": wic_filter_active,
    }


# ── Tool 4: query_fooddata_central ────────────────────────────────────────────

@mcp.tool()
def query_fooddata_central(
    query: str,
    data_type: str = "",
    limit: int = 20,
) -> dict:
    """
    Search USDA FoodData Central for foods by name or keyword.

    Args:
        query: Food name or keyword to search for (e.g. "chicken breast", "oat milk")
        data_type: Optional filter — one of: branded_food | foundation_food |
                   sr_legacy_food | survey_fndds_food | sample_food (leave empty for all)
        limit: Max number of results to return (default 20, max 100)

    Returns:
        dict with list of matching foods (fdc_id, description, data_type, category)
    """
    limit = min(limit, 100)
    params: list = [f"%{query}%"]
    sql = """
        SELECT f.fdc_id, f.description, f.data_type, f.food_category_id,
               fc.description AS category
        FROM food f
        LEFT JOIN food_category fc ON fc.id::text = f.food_category_id
        WHERE f.description ILIKE %s
    """
    if data_type:
        sql += " AND f.data_type = %s"
        params.append(data_type)

    sql += " ORDER BY f.description LIMIT %s"
    params.append(limit)

    rows = fetchall(sql, params)
    return {"query": query, "count": len(rows), "results": rows}


# ── Tool 5: score_foods_by_nutrient_density ───────────────────────────────────

@mcp.tool()
def score_foods_by_nutrient_density(
    fdc_ids: list[int],
    profile_id: str,
) -> dict:
    """
    Score and rank foods by nutrient density against a user's personalised daily values.

    Rewards foods high in protein, fiber, vitamins, and minerals.
    Penalises foods high in sodium, saturated fat, and added sugars.
    All amounts are evaluated per 100g of food.

    Args:
        fdc_ids: List of fdc_id integers to score (from query_fooddata_central)
        profile_id: UUID from capture_user_profile (must have run calculate_personalized_dv)

    Returns:
        dict with ranked list of foods, their scores, and top contributing nutrients
    """
    dv = _get_dv(profile_id)

    if not fdc_ids:
        return {"error": "No fdc_ids provided."}

    placeholders = ",".join(["%s"] * len(fdc_ids))

    food_rows = fetchall(
        f"SELECT fdc_id, description, data_type FROM food WHERE fdc_id IN ({placeholders})",
        fdc_ids,
    )
    food_map = {r["fdc_id"]: r for r in food_rows}

    nutrient_rows = fetchall(
        f"""
        SELECT fn.fdc_id, fn.nutrient_id, fn.amount
        FROM food_nutrient fn
        WHERE fn.fdc_id IN ({placeholders})
          AND fn.nutrient_id IN ({",".join(["%s"] * len(NUTRIENT_ID_MAP))})
          AND fn.amount IS NOT NULL
        """,
        fdc_ids + list(NUTRIENT_ID_MAP.keys()),
    )

    # Group nutrients by fdc_id
    food_nutrients: dict[int, dict[str, float]] = {}
    for row in nutrient_rows:
        fid = row["fdc_id"]
        dv_key = NUTRIENT_ID_MAP.get(row["nutrient_id"])
        if dv_key and row["amount"] is not None:
            food_nutrients.setdefault(fid, {})[dv_key] = float(row["amount"])

    results = []
    for fdc_id in fdc_ids:
        food = food_map.get(fdc_id)
        if not food:
            continue
        amounts = food_nutrients.get(fdc_id, {})
        score = score_food(amounts, dv)

        # Top 3 beneficial nutrients by % DV contribution
        top_nutrients = sorted(
            [
                {"nutrient": k, "amount": round(v, 2), "pct_dv": round(v / dv[k] * 100, 1)}
                for k, v in amounts.items()
                if k in dv and dv[k] > 0 and k not in ("calories_kcal", "sodium_mg", "saturated_fat_g", "added_sugars_g")
            ],
            key=lambda x: x["pct_dv"],
            reverse=True,
        )[:3]

        results.append({
            "fdc_id": fdc_id,
            "description": food["description"],
            "data_type": food["data_type"],
            "nutrient_density_score": score,
            "top_nutrients": top_nutrients,
        })

    results.sort(key=lambda x: x["nutrient_density_score"], reverse=True)
    return {"profile_id": profile_id, "count": len(results), "ranked_foods": results}


# ── Tool 6: check_budget_constraint ──────────────────────────────────────────

@mcp.tool()
def check_budget_constraint(
    profile_id: str,
    fdc_ids: list[int],
) -> dict:
    """
    Estimate whether a set of foods fits within the user's weekly grocery budget.

    Uses serving size from branded_food where available, and category-based

    Args:
        profile_id: UUID from capture_user_profile
        fdc_ids: List of fdc_id integers to cost out

    Returns:
        dict with estimated weekly cost, budget, within_budget flag, and per-item breakdown
    """
    prefs = fetchone("SELECT weekly_budget_usd FROM user_grocery_preference WHERE profile_id = %s", (profile_id,))
    if not prefs:
        raise ValueError("No grocery preferences found. Run capture_preferences first.")
    budget = float(prefs["weekly_budget_usd"])

    placeholders = ",".join(["%s"] * len(fdc_ids))
    food_rows = fetchall(
        f"SELECT fdc_id, description FROM food WHERE fdc_id IN ({placeholders})", fdc_ids
    )
    branded_rows = fetchall(
        f"SELECT fdc_id, branded_food_category, serving_size FROM branded_food WHERE fdc_id IN ({placeholders})",
        fdc_ids,
    )
    branded_map = {r["fdc_id"]: r for r in branded_rows}

    # Build input for bulk pricing
    pricing_input = []
    food_meta = {}
    for food in food_rows:
        fid = food["fdc_id"]
        branded = branded_map.get(fid)
        serving_g = float(branded["serving_size"]) if branded and branded["serving_size"] else 100.0
        pricing_input.append({"food_name": food["description"], "serving_size_g": serving_g})
        food_meta[fid] = {"description": food["description"], "serving_size_g": serving_g}

    # Fetch prices from Open Food Facts + Open Prices concurrently
    prices = asyncio.run(get_grocery_prices_bulk(pricing_input))

    items = []
    total = 0.0
    for i, food in enumerate(food_rows):
        fid = food["fdc_id"]
        price_data = prices[i]
        est_price = price_data["estimated_price_usd"]
        total += est_price
        items.append({
            "fdc_id": fid,
            "description": food["description"],
            "serving_size_g": food_meta[fid]["serving_size_g"],
            "estimated_price_usd": est_price,
            "price_per_100g_usd": price_data["price_per_100g_usd"],
            "barcode": price_data.get("barcode"),
            "price_range": price_data.get("price_range"),
            "price_source": price_data["source"],
        })

    weekly_est = round(total * 7, 2)
    return {
        "profile_id": profile_id,
        "weekly_budget_usd": budget,
        "estimated_weekly_cost_usd": weekly_est,
        "within_budget": weekly_est <= budget,
        "items": items,
    }


# ── Tool 7: optimize_meal_plan ────────────────────────────────────────────────

@mcp.tool()
def optimize_meal_plan(
    profile_id: str,
    candidate_fdc_ids: list[int],
    days: int = 7,
) -> dict:
    """
    Build an optimised multi-day meal plan from a list of candidate foods.

    Scores all candidates by nutrient density, filters out foods that conflict
    with the user's allergies or dietary preferences, checks budget, then
    greedily fills each day's meals to hit the user's personalised daily values.
    Suggests swaps for any nutrients that remain under-covered.

    Args:
        profile_id: UUID from capture_user_profile
        candidate_fdc_ids: Pool of foods to choose from (from query_fooddata_central)
        days: Number of days to plan for (default 7)

    Returns:
        dict with meal_plan, nutrition_coverage percentages, and suggested_swaps
    """
    dv = _get_dv(profile_id)
    allergies, dietary_prefs = _get_user_filters(profile_id)

    # Score all candidates
    scored = score_foods_by_nutrient_density(candidate_fdc_ids, profile_id)["ranked_foods"]

    placeholders = ",".join(["%s"] * len(candidate_fdc_ids))

    # Fetch branded data (ingredients + category) for allergy/preference filtering
    branded_rows = fetchall(
        f"SELECT fdc_id, branded_food_category, ingredients FROM branded_food WHERE fdc_id IN ({placeholders})",
        candidate_fdc_ids,
    )
    branded_map = {r["fdc_id"]: r for r in branded_rows}

    # Fetch nutrient amounts for hard-cap checks (sodium, carbs) and nutrition tracking
    nutrient_rows = fetchall(
        f"""
        SELECT fn.fdc_id, fn.nutrient_id, fn.amount
        FROM food_nutrient fn
        WHERE fn.fdc_id IN ({placeholders})
          AND fn.nutrient_id IN ({",".join(["%s"] * len(NUTRIENT_ID_MAP))})
          AND fn.amount IS NOT NULL
        """,
        candidate_fdc_ids + list(NUTRIENT_ID_MAP.keys()),
    )
    nutrient_map: dict[int, dict[str, float]] = {}
    for row in nutrient_rows:
        fid = row["fdc_id"]
        dv_key = NUTRIENT_ID_MAP.get(row["nutrient_id"])
        if dv_key:
            nutrient_map.setdefault(fid, {})[dv_key] = float(row["amount"])

    # Apply allergy + dietary preference filters
    safe_foods, rejected_foods = _filter_foods(
        scored, branded_map, nutrient_map, allergies, dietary_prefs
    )

    if not safe_foods:
        return {
            "error": "No safe foods remain after applying allergy and dietary preference filters.",
            "rejected_count": len(rejected_foods),
            "filters_applied": {"allergies": allergies, "dietary_preferences": dietary_prefs},
        }

    # Greedy assignment: rotate top-scored safe foods across meals
    meals_per_day = 3
    meal_plan: dict[str, list] = {}
    nutrition_totals: dict[str, float] = {k: 0.0 for k in dv}

    for day in range(1, days + 1):
        day_foods = []
        for meal_idx in range(meals_per_day):
            pick = safe_foods[(day * meals_per_day + meal_idx) % len(safe_foods)]
            day_foods.append({"fdc_id": pick["fdc_id"], "description": pick["description"]})
            for k, v in nutrient_map.get(pick["fdc_id"], {}).items():
                if k in nutrition_totals:
                    nutrition_totals[k] += v
        meal_plan[f"day_{day}"] = day_foods

    # Nutrition coverage: average daily % of DV across the plan
    coverage = {}
    for k, total in nutrition_totals.items():
        dv_val = dv.get(k, 0)
        if dv_val > 0:
            coverage[k] = round((total / days) / dv_val * 100, 1)

    # Suggest swaps for nutrients under 50% coverage
    under_covered = [k for k, pct in coverage.items() if pct < 50]
    suggested_swaps = []
    for nutrient_key in under_covered[:3]:
        best = max(
            safe_foods,
            key=lambda f: nutrient_map.get(f["fdc_id"], {}).get(nutrient_key, 0),
            default=None,
        )
        if best:
            suggested_swaps.append({
                "nutrient_gap": nutrient_key,
                "coverage_pct": coverage.get(nutrient_key, 0),
                "suggested_food": best["description"],
                "fdc_id": best["fdc_id"],
            })

    return {
        "profile_id": profile_id,
        "days": days,
        "filters_applied": {"allergies": allergies, "dietary_preferences": dietary_prefs},
        "foods_considered": len(scored),
        "foods_after_filtering": len(safe_foods),
        "foods_rejected": len(rejected_foods),
        "meal_plan": meal_plan,
        "nutrition_coverage_pct": coverage,
        "suggested_swaps": suggested_swaps,
    }


# ── Tool 8: generate_grocery_list ─────────────────────────────────────────────

@mcp.tool()
def generate_grocery_list(
    profile_id: str,
    meal_plan: dict,
) -> dict:
    """
    Generate a structured grocery list from a meal plan.

    Aggregates all foods from the plan, enriches with branded food data
    (brand name, serving size, UPC), groups by category, applies WIC filter
    if active, and estimates total cost.

    Args:
        profile_id: UUID from capture_user_profile
        meal_plan: The meal_plan dict from optimize_meal_plan (key: day_N, value: list of foods)

    Returns:
        dict with categorised grocery items, quantities, estimated cost, and budget status
    """
    prefs = fetchone(
        "SELECT weekly_budget_usd, wic_filter_active FROM user_grocery_preference WHERE profile_id = %s",
        (profile_id,),
    )
    if not prefs:
        raise ValueError("No grocery preferences found. Run capture_preferences first.")

    budget = float(prefs["weekly_budget_usd"])
    wic_active = str(prefs.get("wic_filter_active", "N")).upper() == "Y"

    # Tally food counts across the plan
    food_counts: dict[int, int] = {}
    for day_foods in meal_plan.values():
        for food in day_foods:
            fid = int(food["fdc_id"])
            food_counts[fid] = food_counts.get(fid, 0) + 1

    if not food_counts:
        return {"error": "meal_plan is empty."}

    fdc_ids = list(food_counts.keys())
    placeholders = ",".join(["%s"] * len(fdc_ids))

    food_rows = fetchall(
        f"SELECT fdc_id, description, data_type FROM food WHERE fdc_id IN ({placeholders})", fdc_ids
    )
    branded_rows = fetchall(
        f"""
        SELECT fdc_id, brand_name, brand_owner, branded_food_category,
               serving_size, serving_size_unit, gtin_upc, household_serving_fulltext
        FROM branded_food WHERE fdc_id IN ({placeholders})
        """,
        fdc_ids,
    )
    branded_map = {r["fdc_id"]: r for r in branded_rows}

    # Bulk price lookup via Open Food Facts + Open Prices
    pricing_input = []
    for food in food_rows:
        fid = food["fdc_id"]
        branded = branded_map.get(fid)
        serving_g = float(branded["serving_size"]) if branded and branded["serving_size"] else 100.0
        pricing_input.append({"food_name": food["description"], "serving_size_g": serving_g})

    prices = asyncio.run(get_grocery_prices_bulk(pricing_input))
    price_map = {food_rows[i]["fdc_id"]: prices[i] for i in range(len(food_rows))}

    categorised: dict[str, list] = {}
    total_cost = 0.0

    for food in food_rows:
        fid = food["fdc_id"]
        branded = branded_map.get(fid)
        category = (branded["branded_food_category"] if branded and branded["branded_food_category"] else "General") or "General"
        serving_g = float(branded["serving_size"]) if branded and branded["serving_size"] else 100.0
        qty = food_counts[fid]
        price_data = price_map[fid]
        est_unit_price = price_data["estimated_price_usd"]
        est_total = round(est_unit_price * qty, 2)
        total_cost += est_total

        item = {
            "fdc_id": fid,
            "description": food["description"],
            "brand": branded["brand_name"] if branded else None,
            "brand_owner": branded["brand_owner"] if branded else None,
            "upc": branded["gtin_upc"] if branded else price_data.get("barcode"),
            "serving_size": f"{serving_g}g",
            "household_serving": branded["household_serving_fulltext"] if branded else None,
            "quantity_needed": qty,
            "estimated_unit_price_usd": est_unit_price,
            "estimated_total_price_usd": est_total,
            "price_range": price_data.get("price_range"),
            "price_source": price_data["source"],
            "wic_eligible": None,  # wire WIC eligibility when grocery API supports it
        }

        if wic_active and item["wic_eligible"] is False:
            continue

        categorised.setdefault(category, []).append(item)

    return {
        "profile_id": profile_id,
        "wic_filter_active": wic_active,
        "grocery_list": categorised,
        "total_estimated_cost_usd": round(total_cost, 2),
        "weekly_budget_usd": budget,
        "within_budget": round(total_cost, 2) <= budget,
    }


# ── Run ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run(transport="stdio")
