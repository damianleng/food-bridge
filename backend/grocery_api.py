"""
Grocery pricing via Open Food Facts + Open Prices (both free, no auth required).

Flow:
  1. search_off(name)        → find product on Open Food Facts → get barcode
  2. get_prices(barcode)     → fetch real crowdsourced prices from Open Prices
  3. estimate_price(name)    → category-based fallback if no price data found

Public APIs used:
  - https://world.openfoodfacts.org/api/v2/  (product search + lookup)
  - https://prices.openfoodfacts.org/api/v1/ (crowdsourced prices)
"""

import httpx
import statistics

# ── Constants ─────────────────────────────────────────────────────────────────

OFF_SEARCH_URL  = "https://world.openfoodfacts.org/cgi/search.pl"
OFF_PRODUCT_URL = "https://world.openfoodfacts.org/api/v2/product/{barcode}.json"
PRICES_URL      = "https://prices.openfoodfacts.org/api/v1/prices"

TIMEOUT = 8.0

# Fallback price estimates (USD per 100g) when no Open Prices data exists
FALLBACK_PRICE_PER_100G: dict[str, float] = {
    # Proteins
    "salmon":     1.80,
    "tuna":       1.40,
    "shrimp":     1.60,
    "fish":       1.50,
    "seafood":    1.50,
    "chicken":    1.00,
    "turkey":     0.90,
    "poultry":    1.00,
    "beef":       1.40,
    "pork":       1.10,
    "lamb":       1.60,
    "meat":       1.20,
    # Dairy & eggs
    "yogurt":     0.60,
    "cheese":     0.90,
    "dairy":      0.50,
    "egg":        0.30,
    "milk":       0.20,
    # Produce
    "avocado":    0.80,
    "berry":      0.90,
    "fruit":      0.45,
    "vegetable":  0.35,
    "produce":    0.40,
    # Grains & legumes
    "oat":        0.35,
    "rice":       0.20,
    "pasta":      0.25,
    "bread":      0.35,
    "grain":      0.30,
    "cereal":     0.50,
    "lentil":     0.28,
    "bean":       0.28,
    "legume":     0.30,
    "tofu":       0.55,
    # Other
    "nut":        1.10,
    "oil":        0.70,
    "sauce":      0.55,
    "frozen":     0.60,
    "snack":      0.80,
    "beverage":   0.20,
    "juice":      0.25,
    "default":    0.55,
}


# ── Open Food Facts ───────────────────────────────────────────────────────────

async def search_off(name: str, max_results: int = 5) -> list[dict]:
    """
    Search Open Food Facts by product name.

    Returns a list of products with barcode, name, category, and serving size.
    """
    params = {
        "search_terms": name,
        "search_simple": 1,
        "action": "process",
        "json": 1,
        "page_size": max_results,
        "fields": "code,product_name,categories_tags,serving_size,quantity,stores_tags,image_url",
    }
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(OFF_SEARCH_URL, params=params)
        resp.raise_for_status()
        data = resp.json()

    products = []
    for p in data.get("products", []):
        barcode = p.get("code")
        if not barcode:
            continue
        products.append({
            "barcode": barcode,
            "name": p.get("product_name", name),
            "categories": p.get("categories_tags", []),
            "serving_size": p.get("serving_size"),
            "quantity": p.get("quantity"),
            "image_url": p.get("image_url"),
        })
    return products


async def get_product_by_barcode(barcode: str) -> dict | None:
    """Fetch a single product from Open Food Facts by barcode."""
    url = OFF_PRODUCT_URL.format(barcode=barcode)
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(url)
        if resp.status_code != 200:
            return None
        data = resp.json()

    if data.get("status") != 1:
        return None

    p = data.get("product", {})
    return {
        "barcode": barcode,
        "name": p.get("product_name"),
        "categories": p.get("categories_tags", []),
        "serving_size": p.get("serving_size"),
        "quantity": p.get("quantity"),
    }


# ── Open Prices ───────────────────────────────────────────────────────────────

async def get_prices(barcode: str, max_entries: int = 20) -> list[dict]:
    """
    Fetch crowdsourced price entries for a product barcode from Open Prices.

    Returns a list of price entries with price, currency, date, and store.
    """
    params = {
        "product_code": barcode,
        "currency": "USD",
        "size": max_entries,
        "order_by": "-date",          # most recent first
    }
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(PRICES_URL, params=params)
        if resp.status_code != 200:
            return []
        data = resp.json()

    entries = []
    for item in data.get("items", []):
        price = item.get("price")
        if price is None:
            continue
        entries.append({
            "price_usd": float(price),
            "currency": item.get("currency", "USD"),
            "date": item.get("date"),
            "store": item.get("location", {}).get("osm_name") if item.get("location") else None,
            "price_per_unit": item.get("price_per_unit"),
        })
    return entries


def summarise_prices(price_entries: list[dict]) -> dict | None:
    """
    Summarise a list of price entries into min / median / max.
    Returns None if no entries.
    """
    if not price_entries:
        return None
    values = [e["price_usd"] for e in price_entries]
    return {
        "min_usd":    round(min(values), 2),
        "median_usd": round(statistics.median(values), 2),
        "max_usd":    round(max(values), 2),
        "sample_size": len(values),
        "source": "open_prices",
    }


# ── Fallback estimator ────────────────────────────────────────────────────────

def _match_category_price(name: str, categories: list[str]) -> float:
    """Match a food to a fallback price per 100g using name + OFF category tags."""
    search_text = " ".join([name.lower()] + [c.lower() for c in categories])
    for key, price in FALLBACK_PRICE_PER_100G.items():
        if key in search_text:
            return price
    return FALLBACK_PRICE_PER_100G["default"]


# ── Main public function ──────────────────────────────────────────────────────

async def get_grocery_price(
    food_name: str,
    serving_size_g: float = 100.0,
) -> dict:
    """
    Get the best available price for a food item.

    Tries Open Food Facts → Open Prices first.
    Falls back to category-based estimate if no live data.

    Args:
        food_name:      Food description (from FDC or branded_food)
        serving_size_g: Serving size in grams (used to scale price per 100g)

    Returns:
        dict with estimated_price_usd, price_per_100g, source, and barcode if found
    """
    barcode: str | None = None
    categories: list[str] = []
    image_url: str | None = None
    price_summary: dict | None = None

    # Step 1: Search Open Food Facts for a matching product
    try:
        products = await search_off(food_name, max_results=3)
        if products:
            best = products[0]
            barcode = best["barcode"]
            categories = best.get("categories", [])
            image_url = best.get("image_url")
    except Exception:
        pass

    # Step 2: Fetch prices from Open Prices using barcode
    if barcode:
        try:
            entries = await get_prices(barcode)
            price_summary = summarise_prices(entries)
        except Exception:
            pass

    # Step 3: Calculate price for the given serving size
    if price_summary:
        # Open Prices returns per-item price — estimate per 100g from median
        # Most entries are per package; scale by serving size as a fraction
        price_per_100g = price_summary["median_usd"] / max(serving_size_g, 1) * 100
        estimated_price = round(price_summary["median_usd"] * (serving_size_g / 100), 2)
        return {
            "food_name": food_name,
            "barcode": barcode,
            "image_url": image_url,
            "serving_size_g": serving_size_g,
            "estimated_price_usd": estimated_price,
            "price_per_100g_usd": round(price_per_100g, 3),
            "price_range": price_summary,
            "source": "open_prices",
        }

    # Fallback: category estimate
    price_per_100g = _match_category_price(food_name, categories)
    estimated_price = round(price_per_100g * (serving_size_g / 100), 2)
    return {
        "food_name": food_name,
        "barcode": barcode,
        "image_url": image_url,
        "serving_size_g": serving_size_g,
        "estimated_price_usd": estimated_price,
        "price_per_100g_usd": price_per_100g,
        "price_range": None,
        "source": "category_estimate",
    }


async def get_grocery_prices_bulk(
    foods: list[dict],
) -> list[dict]:
    """
    Price a list of foods concurrently.

    Args:
        foods: list of dicts with keys: food_name, serving_size_g

    Returns:
        list of price dicts from get_grocery_price, one per input food
    """
    import asyncio
    tasks = [
        get_grocery_price(f["food_name"], f.get("serving_size_g", 100.0))
        for f in foods
    ]
    return await asyncio.gather(*tasks)
