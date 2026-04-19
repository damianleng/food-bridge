"""
LangChain agents for step 4 (meal plan) and step 5 (grocery list).
"""
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.prebuilt import create_react_agent

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

_DB_URI = (
    f"postgresql+psycopg2://"
    f"{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}"
    f"@{os.getenv('POSTGRES_HOST', 'localhost')}:{os.getenv('POSTGRES_PORT', '5433')}"
    f"/{os.getenv('POSTGRES_DB')}"
)

_llm = ChatAnthropic(
    model="claude-haiku-4-5-20251001",
    anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
    temperature=0,
)

_db = SQLDatabase.from_uri(
    _DB_URI,
    include_tables=[
        "food", "food_category", "food_nutrient", "nutrient", "branded_food",
        "user_profile", "user_calculated_dv",
        "user_grocery_preference", "user_dietary_preference", "user_allergy",
    ],
    sample_rows_in_table_info=2,
)

_tools = SQLDatabaseToolkit(db=_db, llm=_llm).get_tools()

_MEAL_PLAN_PROMPT = SystemMessage(content="""You are FoodBridge, a nutrition and meal planning assistant.
You have read-only access to a USDA FoodData Central database via SQL tools.

Key tables:
- food: fdc_id, description, data_type
- food_nutrient: fdc_id, nutrient_id, amount  (per 100g)
- nutrient: id, name, unit_name
- branded_food: fdc_id, brand_name, serving_size
- user_calculated_dv: profile_id + 17 nutrient daily value targets
- user_dietary_preference, user_allergy: user restrictions

Rules:
- Only SELECT queries. Never modify data.
- Limit all queries to 20 rows max.
- Return raw JSON only — no markdown, no prose, no explanation.

Return ONLY this exact JSON shape:
{
  "days": [
    {"day": "Day 1", "meals": [{"name": "Breakfast: Oats + Yogurt"}, {"name": "Lunch: Chicken + Broccoli"}, {"name": "Dinner: Salmon + Rice"}]}
  ],
  "nutrient_coverage": {"calories_kcal": 95, "protein_g": 110, "fiber_g": 88},
  "suggested_swaps": [{"food": "Spinach", "reason": "iron only at 60%"}]
}""")

_meal_plan_agent = create_react_agent(_llm, _tools, prompt=_MEAL_PLAN_PROMPT)

# ── Pricing (single search + single LLM call) ─────────────────────────────────

_search = DuckDuckGoSearchRun()


def get_grocery_prices(grocery_list: dict, zip_code: str) -> dict:
    """One DuckDuckGo search + one LLM call to extract real grocery prices."""
    import re

    # Build short item names — skip known brand prefixes
    _KNOWN_BRANDS = {"whole foods market", "trader joe", "kirkland", "great value", "365"}

    def _short_name(full_name: str) -> str:
        parts = [p.strip() for p in full_name.split(",")]
        if parts and parts[0].lower() in _KNOWN_BRANDS and len(parts) > 1:
            return parts[1]
        return parts[0]

    short_names = []
    for items in grocery_list.values():
        for item in items:
            short_names.append(_short_name(item["name"]))

    query = f"grocery store prices {', '.join(short_names)} near zip {zip_code} 2025"
    try:
        search_results = _search.run(query)
    except Exception as e:
        search_results = f"Search failed: {e}"

    prompt = f"""Based on these web search results, extract current US grocery store prices for each item.

Search results:
{search_results}

Items needed: {', '.join(short_names)}
Location: zip code {zip_code}

Return ONLY this JSON (no markdown, no explanation):
{{
  "items": [
    {{"name": "Chicken Breast", "price_usd": 5.99, "unit": "lb", "store": "Walmart"}},
    {{"name": "Salmon", "price_usd": 10.99, "unit": "lb", "store": "Kroger"}}
  ],
  "total_estimated_usd": 42.50
}}

Use realistic 2025 US grocery prices even if search results are incomplete."""

    response = _llm.invoke([HumanMessage(content=prompt)])
    raw = response.content
    json_match = re.search(r"\{[\s\S]*\}", raw)
    if json_match:
        return json.loads(json_match.group())

    return {"items": [], "total_estimated_usd": 0.0}


def generate_meal_plan(profile_id: str, selected_foods: list[dict]) -> str:
    foods_str = ", ".join(
        f"{f['name']} (fdc_id: {f['fdc_id']})" for f in selected_foods
    )
    message = (
        f"[profile_id: {profile_id}]\n\n"
        f"Selected foods: {foods_str}\n\n"
        "Build a 7-day meal plan using these foods. "
        "Query the user's daily values and food nutrients. "
        "Respect dietary preferences and allergies. "
        "Return the meal plan JSON."
    )
    result = _meal_plan_agent.invoke(
        {"messages": [{"role": "user", "content": message}]},
        config={"recursion_limit": 15},
    )
    return result["messages"][-1].content


