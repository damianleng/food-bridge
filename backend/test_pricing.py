"""Run this inside the backend container to test the pricing function."""
import json
from planner import get_grocery_prices

test_grocery_list = {
    "Meat & Seafood": [
        {"name": "Chicken, broilers or fryers, breast, meat only, cooked, roasted", "fdc_id": 331960, "quantity_needed": 3, "serving_size_g": 450.0},
        {"name": "Fish, salmon, Atlantic, farmed, cooked, dry heat", "fdc_id": 175168, "quantity_needed": 2, "serving_size_g": 450.0},
    ],
    "Grains & Legumes": [
        {"name": "Rice, white, long-grain, regular, enriched, cooked", "fdc_id": 169760, "quantity_needed": 1, "serving_size_g": 500.0},
    ],
    "Produce": [
        {"name": "Broccoli, cooked, boiled, drained, without salt", "fdc_id": 170379, "quantity_needed": 2, "serving_size_g": 300.0},
    ],
    "Other": [
        {"name": "WHOLE FOODS MARKET, ASIAN COOKING ORGANIC SALT-FREE SEASONING", "fdc_id": 123456, "quantity_needed": 1, "serving_size_g": 100.0},
    ],
}

zip_code = "90210"

print("Running pricing...\n")
result = get_grocery_prices(test_grocery_list, zip_code)
print(json.dumps(result, indent=2))
