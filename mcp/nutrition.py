"""
Nutrition calculation logic.

Covers:
  - Mifflin-St Jeor BMR
  - TDEE via activity multiplier
  - Personalized daily values (macros + key micros)
  - Pregnancy / smoking adjustments
"""

from dataclasses import dataclass


# ── Activity multipliers (PAL) ─────────────────────────────────────────────

ACTIVITY_MULTIPLIERS: dict[str, float] = {
    "sedentary":        1.2,
    "lightly_active":   1.375,
    "moderately_active": 1.55,
    "very_active":      1.725,
    "extra_active":     1.9,
}

# ── FDA reference daily intake bases (adult, 2000 kcal diet) ──────────────
# Used as a floor/cap sanity check, not the primary output.

_RDI_BASE = {
    "calories_kcal":   2000.0,
    "protein_g":         50.0,
    "fat_g":             78.0,
    "saturated_fat_g":   20.0,
    "carbohydrates_g":  275.0,
    "fiber_g":           28.0,
    "added_sugars_g":    50.0,
    "sodium_mg":       2300.0,
    "potassium_mg":    4700.0,
    "calcium_mg":      1300.0,
    "iron_mg":           18.0,
    "vitamin_c_mg":      90.0,
    "vitamin_d_iu":     800.0,
    "folate_mcg":       400.0,
    "b12_mcg":            2.4,
    "magnesium_mg":     420.0,
    "zinc_mg":           11.0,
}


@dataclass
class UserProfile:
    height_cm: float
    weight_kg: float
    age: int
    sex: str                  # "male" | "female"
    activity_level: str       # key in ACTIVITY_MULTIPLIERS
    smoking_status: str       # "smoker" | "non_smoker" | "former_smoker"
    pregnancy_status: str     # "not_pregnant" | "pregnant" | "lactating"
    health_goals: list[str]   # e.g. ["weight_loss", "muscle_gain"]
    health_conditions: list[str]  # e.g. ["hypertension", "diabetes"]


def calculate_bmr(profile: UserProfile) -> float:
    """Mifflin-St Jeor equation."""
    if profile.sex.lower() == "male":
        return 10 * profile.weight_kg + 6.25 * profile.height_cm - 5 * profile.age + 5
    return 10 * profile.weight_kg + 6.25 * profile.height_cm - 5 * profile.age - 161


def calculate_tdee(profile: UserProfile) -> float:
    multiplier = ACTIVITY_MULTIPLIERS.get(profile.activity_level, 1.2)
    return calculate_bmr(profile) * multiplier


def _calorie_target(tdee: float, goals: list[str]) -> float:
    if "weight_loss" in goals:
        return tdee - 500          # ~0.5 kg/week deficit
    if "weight_gain" in goals or "muscle_gain" in goals:
        return tdee + 300
    return tdee


def calculate_personalized_dv(profile: UserProfile) -> dict[str, float]:
    """
    Derive a full set of personalised daily values from a UserProfile.
    Returns a flat dict matching the user_calculated_dv table columns.
    """
    tdee   = calculate_tdee(profile)
    target = _calorie_target(tdee, profile.health_goals)
    scale  = target / 2000.0       # scale micros proportionally to calorie target

    goals      = profile.health_goals
    conditions = profile.health_conditions

    # ── Macros ────────────────────────────────────────────────────────────

    # Protein: 0.8 g/kg baseline; bump for muscle gain / older adults
    protein_factor = 1.2 if ("muscle_gain" in goals or profile.age >= 65) else 0.8
    protein_g = protein_factor * profile.weight_kg

    # Fat: 25-35 % of calories; use 30 % baseline
    fat_g = (target * 0.30) / 9

    # Saturated fat: <10 % of calories (AHA tightens to 5-6 % for heart conditions)
    sat_fat_pct = 0.06 if "heart_disease" in conditions else 0.10
    saturated_fat_g = (target * sat_fat_pct) / 9

    # Carbs: remainder after protein + fat calories
    remaining_kcal = target - (protein_g * 4) - (fat_g * 9)
    carbohydrates_g = max(remaining_kcal / 4, 130)   # 130 g minimum (brain glucose)

    # Fiber: 14 g per 1000 kcal (Dietary Guidelines)
    fiber_g = 14 * (target / 1000)

    # Added sugars: <10 % of calories
    added_sugars_g = (target * 0.10) / 4

    # ── Sodium ────────────────────────────────────────────────────────────
    if "hypertension" in conditions or "heart_disease" in conditions or "kidney_disease" in conditions:
        sodium_mg = 1500.0
    else:
        sodium_mg = 2300.0

    # ── Micros (scale with calorie target, then apply condition overrides) ─

    potassium_mg = 4700.0    # AI — not scaled (fixed adequate intake)
    calcium_mg   = 1300.0 if profile.age >= 51 or profile.sex.lower() == "female" else 1000.0
    iron_mg      = 18.0 if (profile.sex.lower() == "female" and profile.age < 51) else 8.0
    vitamin_c_mg = 75.0 if profile.sex.lower() == "female" else 90.0
    vitamin_d_iu = 800.0 if profile.age >= 70 else 600.0
    folate_mcg   = 400.0
    b12_mcg      = 2.4
    magnesium_mg = 320.0 if profile.sex.lower() == "female" else 420.0
    zinc_mg      = 8.0  if profile.sex.lower() == "female" else 11.0

    # ── Pregnancy / lactation adjustments ─────────────────────────────────
    if profile.pregnancy_status == "pregnant":
        target          += 340          # 2nd trimester bump
        carbohydrates_g += 45
        protein_g       += 25
        folate_mcg       = 600.0
        iron_mg          = 27.0
        calcium_mg       = 1000.0
        vitamin_d_iu     = 600.0

    elif profile.pregnancy_status == "lactating":
        target          += 500
        protein_g       += 25
        folate_mcg       = 500.0
        calcium_mg       = 1000.0
        vitamin_c_mg     = 120.0

    # ── Smoking adjustment ────────────────────────────────────────────────
    # Smokers need ~35 mg extra vitamin C (NIH recommendation)
    if profile.smoking_status == "smoker":
        vitamin_c_mg += 35.0

    # ── Diabetes: reduce added sugars & refined carbs ─────────────────────
    if "diabetes" in conditions or "prediabetes" in conditions:
        added_sugars_g = min(added_sugars_g, 25.0)
        fiber_g        = max(fiber_g, 35.0)    # higher fiber helps glycaemic control

    return {
        "calories_kcal":   round(target, 1),
        "protein_g":       round(protein_g, 1),
        "fat_g":           round(fat_g, 1),
        "saturated_fat_g": round(saturated_fat_g, 1),
        "carbohydrates_g": round(carbohydrates_g, 1),
        "fiber_g":         round(fiber_g, 1),
        "added_sugars_g":  round(added_sugars_g, 1),
        "sodium_mg":       round(sodium_mg, 1),
        "potassium_mg":    round(potassium_mg, 1),
        "calcium_mg":      round(calcium_mg, 1),
        "iron_mg":         round(iron_mg, 1),
        "vitamin_c_mg":    round(vitamin_c_mg, 1),
        "vitamin_d_iu":    round(vitamin_d_iu, 1),
        "folate_mcg":      round(folate_mcg, 1),
        "b12_mcg":         round(b12_mcg, 1),
        "magnesium_mg":    round(magnesium_mg, 1),
        "zinc_mg":         round(zinc_mg, 1),
    }


# ── Nutrient density scoring ───────────────────────────────────────────────

# Nutrient IDs from the USDA nutrient table that we care about, mapped to
# the DV key they correspond to.  Expand as needed.
NUTRIENT_ID_MAP: dict[int, str] = {
    1008: "calories_kcal",
    1003: "protein_g",
    1004: "fat_g",
    1258: "saturated_fat_g",
    1005: "carbohydrates_g",
    1079: "fiber_g",
    1235: "added_sugars_g",
    1093: "sodium_mg",
    1092: "potassium_mg",
    1087: "calcium_mg",
    1089: "iron_mg",
    1162: "vitamin_c_mg",
    1114: "vitamin_d_iu",
    1177: "folate_mcg",
    1178: "b12_mcg",
    1090: "magnesium_mg",
    1095: "zinc_mg",
}

# Nutrients where a higher amount is *bad* — penalise instead of reward
PENALTY_NUTRIENTS = {"calories_kcal", "saturated_fat_g", "sodium_mg", "added_sugars_g"}

# Weight of each nutrient in the composite score (beneficial ones)
NUTRIENT_WEIGHTS: dict[str, float] = {
    "protein_g":       2.0,
    "fiber_g":         2.0,
    "potassium_mg":    1.5,
    "calcium_mg":      1.5,
    "iron_mg":         1.5,
    "vitamin_c_mg":    1.0,
    "vitamin_d_iu":    1.5,
    "folate_mcg":      1.0,
    "b12_mcg":         1.0,
    "magnesium_mg":    1.0,
    "zinc_mg":         1.0,
    "carbohydrates_g": 0.5,
    "fat_g":           0.5,
}

PENALTY_WEIGHTS: dict[str, float] = {
    "calories_kcal":   0.5,
    "saturated_fat_g": 1.5,
    "sodium_mg":       1.5,
    "added_sugars_g":  1.5,
}


def score_food(
    nutrient_amounts: dict[str, float],   # {dv_key: amount per 100 g}
    dv: dict[str, float],                 # personalised DV from calculate_personalized_dv
) -> float:
    """
    Return a nutrient-density score for a food given its nutrient amounts
    per 100 g and the user's personalised daily values.

    Positive score: food contributes well to DV targets.
    Higher is better.
    """
    score = 0.0
    for key, weight in NUTRIENT_WEIGHTS.items():
        dv_val = dv.get(key, 0)
        if dv_val > 0:
            pct = nutrient_amounts.get(key, 0) / dv_val
            score += weight * min(pct, 1.0)   # cap at 100 % contribution

    for key, weight in PENALTY_WEIGHTS.items():
        dv_val = dv.get(key, 0)
        if dv_val > 0:
            pct = nutrient_amounts.get(key, 0) / dv_val
            score -= weight * pct

    return round(score, 4)
