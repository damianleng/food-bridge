import asyncio
from pathlib import Path

import pandas as pd

from db import fetch_all
from grocery_api import get_grocery_prices_bulk
from ml_ranker import build_feature_row, train_ranker, MODEL_PATH
from nutrition import NUTRIENT_ID_MAP, score_food, _RDI_BASE

SEED_TERMS = [
    "chicken", "salmon", "tuna", "egg", "yogurt", "milk",
    "spinach", "broccoli", "carrot", "tomato", "avocado",
    "bean", "lentil", "chickpea", "tofu", "rice", "oat",
    "pasta", "bread", "banana", "apple", "berry",
]


def build_training_frame(limit_per_term: int = 50) -> pd.DataFrame:
    candidates_by_id = {}

    for term in SEED_TERMS:
        rows = fetch_all(
            "SELECT fdc_id, description, data_type FROM food WHERE description ILIKE %s LIMIT %s",
            (f"%{term}%", limit_per_term),
        )
        for row in rows:
            candidates_by_id[int(row["fdc_id"])] = row

    candidates = list(candidates_by_id.values())
    if not candidates:
        raise ValueError("No candidate foods found in DB.")

    fdc_ids = [int(r["fdc_id"]) for r in candidates]

    nutrient_rows = fetch_all(
        "SELECT fdc_id, nutrient_id, amount FROM food_nutrient WHERE fdc_id = ANY(%s) AND nutrient_id = ANY(%s)",
        (fdc_ids, list(NUTRIENT_ID_MAP.keys())),
    )

    nutrient_map: dict[int, dict[str, float]] = {}
    for row in nutrient_rows:
        fid = int(row["fdc_id"])
        dv_key = NUTRIENT_ID_MAP.get(int(row["nutrient_id"]))
        if dv_key and row["amount"] is not None:
            nutrient_map.setdefault(fid, {})[dv_key] = float(row["amount"])

    price_inputs = [{"food_name": r["description"], "serving_size_g": 100.0} for r in candidates]
    price_outputs = asyncio.run(get_grocery_prices_bulk(price_inputs))

    rows = []
    for food, price_data in zip(candidates, price_outputs):
        fid = int(food["fdc_id"])
        nutrients = nutrient_map.get(fid, {})
        heuristic = score_food(nutrients, _RDI_BASE)

        feature_row = build_feature_row(
            nutrient_amounts=nutrients,
            dv=_RDI_BASE,
            heuristic_score=heuristic,
            price_data=price_data,
            cuisine_match=0,
            health_conditions=[],
            health_goals=[],
        )
        feature_row["fdc_id"] = fid
        feature_row["name"] = food["description"]
        feature_row["data_type"] = food["data_type"]
        rows.append(feature_row)

    return pd.DataFrame(rows)


if __name__ == "__main__":
    df = build_training_frame()
    model, metrics, labeled = train_ranker(df, MODEL_PATH)

    artifacts_dir = Path(__file__).resolve().parent / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    df.to_csv(artifacts_dir / "ranker_training_frame.csv", index=False)
    labeled.to_csv(artifacts_dir / "ranker_labeled_frame.csv", index=False)

    print("Saved model to:", MODEL_PATH)
    print("Metrics:", metrics)
    print("Training rows:", len(df))
    print("Labeled rows:", len(labeled))
