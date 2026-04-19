"""
Direct DB operations for steps 1 & 2 — no Claude / MCP involved.
"""

from db import execute, execute_returning, fetch_all, fetch_one
from nutrition import UserProfile, calculate_personalized_dv as _calc_dv, NUTRIENT_ID_MAP, NUTRIENT_WEIGHTS, score_food, _RDI_BASE


def _snake(s: str) -> str:
    return s.strip().lower().replace(" ", "_")


def create_profile(
    height_cm: float,
    weight_kg: float,
    age: int,
    sex: str,
    activity_level: str,
    smoking_status: str,
    household_size_adults: int,
    household_size_children: int,
    health_goals: list[str],
    health_conditions: list[str],
    medications: list[str],
) -> str:
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
            height_cm, weight_kg, age, sex.lower(), _snake(activity_level),
            _snake(smoking_status), "not_pregnant",
            household_size_adults, household_size_children,
        ),
    )
    profile_id = str(row["profile_id"])

    for goal in health_goals:
        g = _snake(goal)
        if g and g != "none":
            execute(
                "INSERT INTO user_health_goal (profile_id, goal) VALUES (%s,%s)",
                (profile_id, g),
            )

    for cond in health_conditions:
        if cond and cond.lower() != "none":
            execute(
                "INSERT INTO user_health_condition (profile_id, condition_name) VALUES (%s,%s)",
                (profile_id, cond),
            )

    for med in medications:
        if med.strip():
            execute(
                "INSERT INTO user_medication (profile_id, medication_name) VALUES (%s,%s)",
                (profile_id, med.strip()),
            )

    # Calculate and persist personalised daily values
    profile = UserProfile(
        height_cm=height_cm,
        weight_kg=weight_kg,
        age=age,
        sex=sex.lower(),
        activity_level=_snake(activity_level),
        smoking_status=_snake(smoking_status),
        pregnancy_status="not_pregnant",
        health_goals=[_snake(g) for g in health_goals if g and g.lower() != "none"],
        health_conditions=[c for c in health_conditions if c and c.lower() != "none"],
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

    return profile_id


def save_preferences(
    profile_id: str,
    weekly_budget_usd: float,
    zip_code: str,
    dietary_preferences: list[str],
    allergies: list[str],
    cuisine_preferences: list[str],
    wic_filter_active: bool,
) -> None:
    execute(
        """
        INSERT INTO user_grocery_preference (profile_id, weekly_budget_usd, zip_code, wic_filter_active)
        VALUES (%s,%s,%s,%s)
        ON CONFLICT (profile_id) DO UPDATE
            SET weekly_budget_usd = EXCLUDED.weekly_budget_usd,
                zip_code          = EXCLUDED.zip_code,
                wic_filter_active = EXCLUDED.wic_filter_active,
                updated_at        = NOW()
        """,
        (profile_id, weekly_budget_usd, zip_code, "Y" if wic_filter_active else "N"),
    )

    execute("DELETE FROM user_dietary_preference WHERE profile_id = %s", (profile_id,))
    for pref in dietary_preferences:
        p = _snake(pref)
        if p:
            execute(
                "INSERT INTO user_dietary_preference (profile_id, preference) VALUES (%s,%s)",
                (profile_id, p),
            )

    execute("DELETE FROM user_allergy WHERE profile_id = %s", (profile_id,))
    for allergen in allergies:
        a = allergen.strip().lower()
        if a:
            execute(
                "INSERT INTO user_allergy (profile_id, allergen) VALUES (%s,%s)",
                (profile_id, a),
            )

    execute("DELETE FROM user_cuisine_preference WHERE profile_id = %s", (profile_id,))
    for cuisine in cuisine_preferences:
        if cuisine.strip():
            execute(
                "INSERT INTO user_cuisine_preference (profile_id, cuisine) VALUES (%s,%s)",
                (profile_id, cuisine),
            )


# ── Food search ───────────────────────────────────────────────────────────────

_NUTRIENT_IDS = list(NUTRIENT_ID_MAP.keys())

_CUISINE_KEYWORDS: dict[str, list[str]] = {
    "Asian":          ["tofu", "bok choy", "rice", "soy", "edamame", "miso", "tempeh",
                       "noodle", "sesame", "ginger", "mung", "lemongrass", "daikon"],
    "Mexican":        ["black bean", "pinto bean", "corn", "avocado", "jalapeño",
                       "cilantro", "lime", "tortilla", "chili", "salsa", "tomatillo"],
    "Mediterranean":  ["olive", "hummus", "chickpea", "feta", "quinoa", "lentil",
                       "eggplant", "tahini", "couscous", "spinach", "artichoke", "sardine"],
    "Italian":        ["pasta", "tomato", "basil", "mozzarella", "ricotta",
                       "zucchini", "parmesan", "polenta", "cannellini"],
    "Middle Eastern": ["hummus", "lentil", "chickpea", "tahini", "lamb",
                       "pomegranate", "bulgur", "falafel", "sumac", "za'atar"],
    "American":       ["chicken", "beef", "potato", "corn", "turkey",
                       "sweet potato", "blueberry", "cranberry", "pumpkin"],
}

_BENEFICIAL = {
    k for k in NUTRIENT_WEIGHTS
    if k not in {"calories_kcal", "saturated_fat_g", "sodium_mg", "added_sugars_g", "fat_g", "carbohydrates_g"}
}

_NUTRIENT_LABELS = {
    "protein_g": "Protein",
    "fiber_g": "Fiber",
    "potassium_mg": "Potassium",
    "calcium_mg": "Calcium",
    "iron_mg": "Iron",
    "vitamin_c_mg": "Vitamin C",
    "vitamin_d_iu": "Vitamin D",
    "folate_mcg": "Folate",
    "b12_mcg": "Vitamin B12",
    "magnesium_mg": "Magnesium",
    "zinc_mg": "Zinc",
}


# ── Grocery list derivation ───────────────────────────────────────────────────

_CATEGORY_RULES: list[tuple[list[str], str]] = [
    (["chicken", "beef", "pork", "turkey", "lamb", "bison", "meat"], "Meat & Seafood"),
    (["salmon", "tuna", "tilapia", "cod", "shrimp", "fish", "crab", "lobster", "seafood"], "Meat & Seafood"),
    (["milk", "yogurt", "cheese", "butter", "cream", "whey"], "Dairy & Eggs"),
    (["egg"], "Dairy & Eggs"),
    (["broccoli", "spinach", "kale", "lettuce", "carrot", "tomato", "cucumber",
      "pepper", "onion", "garlic", "potato", "sweet potato", "zucchini",
      "apple", "banana", "berry", "orange", "mango", "fruit", "vegetable"], "Produce"),
    (["oat", "rice", "pasta", "bread", "quinoa", "barley", "wheat", "flour", "cereal", "grain"], "Grains & Legumes"),
    (["bean", "lentil", "chickpea", "pea", "legume", "tofu", "tempeh"], "Grains & Legumes"),
    (["oil", "olive", "butter", "ghee", "avocado oil", "coconut oil"], "Fats & Oils"),
    (["nut", "almond", "walnut", "cashew", "peanut", "seed", "tahini"], "Nuts & Seeds"),
]

_DEFAULT_SERVING_G: dict[str, float] = {
    "Meat & Seafood": 450.0,
    "Dairy & Eggs":   500.0,
    "Produce":        300.0,
    "Grains & Legumes": 500.0,
    "Fats & Oils":    250.0,
    "Nuts & Seeds":   200.0,
    "Other":          300.0,
}

_DEFAULT_QTY: dict[str, int] = {
    "Meat & Seafood": 3,
    "Dairy & Eggs":   2,
    "Produce":        2,
    "Grains & Legumes": 1,
    "Fats & Oils":    1,
    "Nuts & Seeds":   1,
    "Other":          2,
}


def _categorise(name: str) -> str:
    lower = name.lower()
    for keywords, category in _CATEGORY_RULES:
        if any(k in lower for k in keywords):
            return category
    return "Other"


def derive_grocery_list(selected_foods: list[dict]) -> dict:
    fdc_ids = [int(f["fdc_id"]) for f in selected_foods]

    # Get serving sizes from branded_food where available
    branded_rows = fetch_all(
        "SELECT fdc_id, serving_size FROM branded_food WHERE fdc_id = ANY(%s)",
        (fdc_ids,),
    )
    serving_map: dict[int, float] = {
        int(r["fdc_id"]): float(r["serving_size"])
        for r in branded_rows
        if r["serving_size"] is not None
    }

    grocery_list: dict[str, list[dict]] = {}

    for food in selected_foods:
        fid = int(food["fdc_id"])
        name = food["name"]
        category = _categorise(name)
        serving_size_g = serving_map.get(fid, _DEFAULT_SERVING_G.get(category, 300.0))
        quantity_needed = _DEFAULT_QTY.get(category, 2)

        grocery_list.setdefault(category, []).append({
            "name": name,
            "fdc_id": fid,
            "quantity_needed": quantity_needed,
            "serving_size_g": round(serving_size_g, 1),
        })

    return {"grocery_list": grocery_list}


def search_foods(query: str, profile_id: str | None = None, limit: int = 20) -> list[dict]:
    candidates = fetch_all(
        "SELECT fdc_id, description, data_type FROM food WHERE description ILIKE %s LIMIT 100",
        (f"%{query}%",),
    )
    if not candidates:
        return []

    # Fetch user's cuisine preferences and allergens in parallel
    cuisine_keywords: list[str] = []
    if profile_id:
        allergy_rows = fetch_all(
            "SELECT allergen FROM user_allergy WHERE profile_id = %s", (profile_id,)
        )
        allergens = [r["allergen"].lower() for r in allergy_rows]
        if allergens:
            candidates = [
                c for c in candidates
                if not any(a in c["description"].lower() for a in allergens)
            ]

        cuisine_rows = fetch_all(
            "SELECT cuisine FROM user_cuisine_preference WHERE profile_id = %s", (profile_id,)
        )
        for row in cuisine_rows:
            keywords = _CUISINE_KEYWORDS.get(row["cuisine"], [])
            cuisine_keywords.extend(keywords)

    if not candidates:
        return []

    fdc_ids = [int(r["fdc_id"]) for r in candidates]

    # Fetch key nutrients for all candidates in one query
    nutrient_rows = fetch_all(
        "SELECT fdc_id, nutrient_id, amount FROM food_nutrient WHERE fdc_id = ANY(%s) AND nutrient_id = ANY(%s)",
        (fdc_ids, _NUTRIENT_IDS),
    )

    nutrient_map: dict[int, dict[str, float]] = {}
    for row in nutrient_rows:
        fid = int(row["fdc_id"])
        dv_key = NUTRIENT_ID_MAP.get(int(row["nutrient_id"]))
        if dv_key and row["amount"] is not None:
            nutrient_map.setdefault(fid, {})[dv_key] = float(row["amount"])

    # Load user's personalized DV (fall back to RDI baseline)
    dv: dict[str, float] = dict(_RDI_BASE)
    if profile_id:
        dv_row = fetch_one(
            "SELECT * FROM user_calculated_dv WHERE profile_id = %s", (profile_id,)
        )
        if dv_row:
            dv = {}
            for k, v in dv_row.items():
                if k == "profile_id" or v is None:
                    continue
                try:
                    dv[k] = float(v)
                except (TypeError, ValueError):
                    pass

    results = []
    for food in candidates:
        fid = int(food["fdc_id"])
        nutrients = nutrient_map.get(fid, {})
        raw = score_food(nutrients, dv)
        scaled = round(min(100.0, max(0.0, raw * 25)), 1)

        top = sorted(
            [k for k in nutrients if k in _BENEFICIAL and dv.get(k, 0) > 0],
            key=lambda k: nutrients[k] / dv[k],
            reverse=True,
        )[:3]

        # Boost score for culturally relevant foods
        name_lower = food["description"].lower()
        if cuisine_keywords and any(kw in name_lower for kw in cuisine_keywords):
            scaled = min(100.0, scaled + 15.0)

        results.append({
            "fdc_id": fid,
            "name": food["description"],
            "data_type": food["data_type"],
            "score": scaled,
            "top_nutrients": [_NUTRIENT_LABELS.get(k, k) for k in top],
        })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:limit]
