"""
FoodBridge FastAPI backend.

Steps 1 & 2 hit the DB directly.
Steps 3-5 will be handled by a LangChain agent (coming soon).
"""

import uuid

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import user
import planner

app = FastAPI(title="FoodBridge API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Step 1: Profile ───────────────────────────────────────────────────────────

class ProfileRequest(BaseModel):
    session_id: str | None = None
    height_cm: float
    weight_kg: float
    age: int
    sex: str
    activity_level: str
    smoking_status: str
    household_size_adults: int = 1
    household_size_children: int = 0
    health_goals: list[str] = []
    health_conditions: list[str] = []
    medications: list[str] = []


class ProfileResponse(BaseModel):
    session_id: str
    profile_id: str


@app.post("/profile", response_model=ProfileResponse)
def create_profile(req: ProfileRequest):
    session_id = req.session_id or str(uuid.uuid4())
    try:
        profile_id = user.create_profile(
            height_cm=req.height_cm,
            weight_kg=req.weight_kg,
            age=req.age,
            sex=req.sex,
            activity_level=req.activity_level,
            smoking_status=req.smoking_status,
            household_size_adults=req.household_size_adults,
            household_size_children=req.household_size_children,
            health_goals=req.health_goals,
            health_conditions=req.health_conditions,
            medications=req.medications,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return ProfileResponse(session_id=session_id, profile_id=profile_id)


# ── Step 2: Preferences ───────────────────────────────────────────────────────

class PreferencesRequest(BaseModel):
    session_id: str | None = None
    profile_id: str
    weekly_budget_usd: float
    zip_code: str
    dietary_preferences: list[str] = []
    allergies: list[str] = []
    cuisine_preferences: list[str] = []
    wic_filter_active: bool = False


@app.post("/preferences")
def save_preferences(req: PreferencesRequest):
    try:
        user.save_preferences(
            profile_id=req.profile_id,
            weekly_budget_usd=req.weekly_budget_usd,
            zip_code=req.zip_code,
            dietary_preferences=req.dietary_preferences,
            allergies=req.allergies,
            cuisine_preferences=req.cuisine_preferences,
            wic_filter_active=req.wic_filter_active,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return {"status": "ok"}


# ── Step 3: Food search ───────────────────────────────────────────────────────

class SearchRequest(BaseModel):
    query: str
    profile_id: str | None = None


class FoodResult(BaseModel):
    fdc_id: int
    name: str
    data_type: str | None = None
    score: float
    top_nutrients: list[str]


@app.post("/search", response_model=list[FoodResult])
def search_foods(req: SearchRequest):
    try:
        results = user.search_foods(req.query, profile_id=req.profile_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return results


# ── Step 4: Meal plan ────────────────────────────────────────────────────────

class SelectedFood(BaseModel):
    fdc_id: int
    name: str


class MealPlanRequest(BaseModel):
    profile_id: str
    selected_foods: list[SelectedFood]


@app.post("/meal-plan")
def meal_plan(req: MealPlanRequest):
    try:
        result = planner.generate_meal_plan(
            req.profile_id,
            [f.model_dump() for f in req.selected_foods],
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return {"response": result}


# ── Step 5: Grocery list ──────────────────────────────────────────────────────

class GroceryListRequest(BaseModel):
    profile_id: str
    selected_foods: list[SelectedFood]


@app.post("/grocery-list")
async def grocery_list(req: GroceryListRequest):
    import asyncio

    try:
        data = user.derive_grocery_list([f.model_dump() for f in req.selected_foods])
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    grocery_list_data = data.get("grocery_list", {})

    # Fetch zip code for location-aware pricing
    zip_code = "10001"
    try:
        import db as _db
        pref_row = _db.fetch_one(
            "SELECT zip_code FROM user_grocery_preference WHERE profile_id = %s",
            (req.profile_id,),
        )
        if pref_row and pref_row.get("zip_code"):
            zip_code = pref_row["zip_code"]
    except Exception:
        pass

    # Use web search agent for real prices
    try:
        loop = asyncio.get_event_loop()
        price_data = await loop.run_in_executor(
            None,
            lambda: planner.get_grocery_prices(grocery_list_data, zip_code),
        )
    except Exception:
        price_data = {"items": [], "total_estimated_usd": 0.0}

    # Match agent prices back to grocery list items by name (fuzzy word overlap)
    price_map: dict[str, dict] = {}
    for entry in price_data.get("items", []):
        name_key = entry.get("name", "").lower()
        price_map[name_key] = entry

    def _best_match(food_name: str) -> dict | None:
        words = set(food_name.lower().replace(",", " ").split())
        best, best_score = None, 0
        for k, v in price_map.items():
            k_words = set(k.replace(",", " ").split())
            score = len(words & k_words)
            if score > best_score:
                best, best_score = v, score
        return best if best_score >= 1 else None

    total = 0.0
    for category, items in grocery_list_data.items():
        for item in items:
            matched = _best_match(item["name"])
            qty = max(1, min(int(item.get("quantity_needed", 1)), 10))
            item["quantity_needed"] = qty
            if matched:
                item["estimated_unit_price_usd"] = round(float(matched.get("price_usd", 0)), 2)
                item["price_unit"] = matched.get("unit", "")
                item["price_store"] = matched.get("store", "")
                item["price_source"] = "web_search"
            else:
                item["estimated_unit_price_usd"] = 0.0
                item["price_source"] = "unavailable"
            total += item["estimated_unit_price_usd"] * qty

    agent_total = price_data.get("total_estimated_usd", 0.0)
    return {
        "total_estimated_cost_usd": round(agent_total if agent_total > 0 else total, 2),
        "grocery_list": grocery_list_data,
    }


class ResetRequest(BaseModel):
    session_id: str


@app.post("/reset")
def reset(req: ResetRequest):
    return {"session_id": req.session_id, "status": "cleared"}


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok"}
