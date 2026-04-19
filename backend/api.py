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
    from grocery_api import get_grocery_price

    try:
        data = user.derive_grocery_list([f.model_dump() for f in req.selected_foods])
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    grocery_list_data = data.get("grocery_list", {})

    # Collect all items for bulk price lookup
    all_items = []
    for items in grocery_list_data.values():
        if isinstance(items, list):
            all_items.extend(items)

    prices = await asyncio.gather(
        *[get_grocery_price(it.get("name", ""), float(it.get("serving_size_g", 100))) for it in all_items],
        return_exceptions=True,
    )

    total = 0.0
    for item, price_result in zip(all_items, prices):
        if isinstance(price_result, Exception):
            item["estimated_unit_price_usd"] = 0.0
            item["price_source"] = "unavailable"
        else:
            qty = max(1, min(int(item.get("quantity_needed", 1)), 10))
            item["quantity_needed"] = qty
            item["estimated_unit_price_usd"] = price_result["estimated_price_usd"]
            item["price_source"] = price_result["source"]
            total += price_result["estimated_price_usd"] * qty

    return {
        "total_estimated_cost_usd": round(total, 2),
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
