from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

MODEL_PATH = Path(__file__).resolve().parent / "artifacts" / "food_ranker.joblib"

FEATURE_COLUMNS = [
    "protein_pct_dv",
    "fiber_pct_dv",
    "potassium_pct_dv",
    "calcium_pct_dv",
    "iron_pct_dv",
    "vitamin_c_pct_dv",
    "vitamin_d_pct_dv",
    "folate_pct_dv",
    "b12_pct_dv",
    "magnesium_pct_dv",
    "zinc_pct_dv",
    "carbohydrates_pct_dv",
    "fat_pct_dv",
    "calories_pct_dv",
    "saturated_fat_pct_dv",
    "sodium_pct_dv",
    "added_sugars_pct_dv",
    "heuristic_score",
    "estimated_price_usd",
    "price_per_100g_usd",
    "has_open_prices",
    "has_fallback_price",
    "cuisine_match",
    "cond_diabetes",
    "cond_hypertension",
    "cond_heart_disease",
    "goal_weight_loss",
    "goal_muscle_gain",
]


def _safe_ratio(amount: float | int | None, dv: float | int | None) -> float:
    amount = float(amount or 0.0)
    dv = float(dv or 0.0)
    if dv <= 0:
        return 0.0
    return amount / dv


def _flag(values: list[str] | None, key: str) -> int:
    values = [str(v).lower() for v in (values or [])]
    return int(key.lower() in values)


def build_feature_row(
    nutrient_amounts: dict[str, float],
    dv: dict[str, float],
    heuristic_score: float,
    price_data: dict[str, Any] | None = None,
    cuisine_match: int = 0,
    health_conditions: list[str] | None = None,
    health_goals: list[str] | None = None,
) -> dict[str, float]:
    price_data = price_data or {}

    return {
        "protein_pct_dv": _safe_ratio(nutrient_amounts.get("protein_g"), dv.get("protein_g")),
        "fiber_pct_dv": _safe_ratio(nutrient_amounts.get("fiber_g"), dv.get("fiber_g")),
        "potassium_pct_dv": _safe_ratio(nutrient_amounts.get("potassium_mg"), dv.get("potassium_mg")),
        "calcium_pct_dv": _safe_ratio(nutrient_amounts.get("calcium_mg"), dv.get("calcium_mg")),
        "iron_pct_dv": _safe_ratio(nutrient_amounts.get("iron_mg"), dv.get("iron_mg")),
        "vitamin_c_pct_dv": _safe_ratio(nutrient_amounts.get("vitamin_c_mg"), dv.get("vitamin_c_mg")),
        "vitamin_d_pct_dv": _safe_ratio(nutrient_amounts.get("vitamin_d_iu"), dv.get("vitamin_d_iu")),
        "folate_pct_dv": _safe_ratio(nutrient_amounts.get("folate_mcg"), dv.get("folate_mcg")),
        "b12_pct_dv": _safe_ratio(nutrient_amounts.get("b12_mcg"), dv.get("b12_mcg")),
        "magnesium_pct_dv": _safe_ratio(nutrient_amounts.get("magnesium_mg"), dv.get("magnesium_mg")),
        "zinc_pct_dv": _safe_ratio(nutrient_amounts.get("zinc_mg"), dv.get("zinc_mg")),
        "carbohydrates_pct_dv": _safe_ratio(nutrient_amounts.get("carbohydrates_g"), dv.get("carbohydrates_g")),
        "fat_pct_dv": _safe_ratio(nutrient_amounts.get("fat_g"), dv.get("fat_g")),
        "calories_pct_dv": _safe_ratio(nutrient_amounts.get("calories_kcal"), dv.get("calories_kcal")),
        "saturated_fat_pct_dv": _safe_ratio(nutrient_amounts.get("saturated_fat_g"), dv.get("saturated_fat_g")),
        "sodium_pct_dv": _safe_ratio(nutrient_amounts.get("sodium_mg"), dv.get("sodium_mg")),
        "added_sugars_pct_dv": _safe_ratio(nutrient_amounts.get("added_sugars_g"), dv.get("added_sugars_g")),
        "heuristic_score": float(heuristic_score),
        "estimated_price_usd": float(price_data.get("estimated_price_usd", 0.0) or 0.0),
        "price_per_100g_usd": float(price_data.get("price_per_100g_usd", 0.0) or 0.0),
        "has_open_prices": int(price_data.get("source") == "open_prices"),
        "has_fallback_price": int(price_data.get("source") == "category_estimate"),
        "cuisine_match": int(cuisine_match),
        "cond_diabetes": _flag(health_conditions, "diabetes"),
        "cond_hypertension": _flag(health_conditions, "hypertension"),
        "cond_heart_disease": _flag(health_conditions, "heart_disease"),
        "goal_weight_loss": _flag(health_goals, "weight_loss"),
        "goal_muscle_gain": _flag(health_goals, "muscle_gain"),
    }


def _normalize(values: list[float] | np.ndarray) -> np.ndarray:
    arr = np.asarray(values, dtype=float)
    if len(arr) == 0:
        return arr
    lo, hi = arr.min(), arr.max()
    if hi - lo < 1e-12:
        return np.zeros_like(arr)
    return (arr - lo) / (hi - lo)


def create_weak_labels(df: pd.DataFrame) -> pd.DataFrame:
    """
    Weak supervision:
    - positives = strong heuristic, reasonable price, low penalties
    - negatives = weak heuristic or expensive or high sodium/sugar/sat fat
    """
    out = df.copy()
    if out.empty:
        return out

    q_hi = out["heuristic_score"].quantile(0.75)
    q_lo = out["heuristic_score"].quantile(0.35)
    q_price = out["price_per_100g_usd"].quantile(0.85) if (out["price_per_100g_usd"] > 0).any() else np.inf

    positive = (
        (out["heuristic_score"] >= q_hi)
        & (out["price_per_100g_usd"] <= q_price)
        & (out["sodium_pct_dv"] <= 0.45)
        & (out["added_sugars_pct_dv"] <= 0.40)
        & (out["saturated_fat_pct_dv"] <= 0.40)
    )

    negative = (
        (out["heuristic_score"] <= q_lo)
        | (out["price_per_100g_usd"] > q_price)
        | (out["sodium_pct_dv"] > 0.70)
        | (out["added_sugars_pct_dv"] > 0.60)
        | (out["saturated_fat_pct_dv"] > 0.60)
    )

    out["label"] = np.where(positive, 1, np.where(negative, 0, np.nan))
    out = out.dropna(subset=["label"]).copy()
    out["label"] = out["label"].astype(int)
    return out


def train_ranker(
    feature_df: pd.DataFrame,
    model_path: Path | str = MODEL_PATH,
    random_state: int = 42,
):
    model_path = Path(model_path)
    labeled = create_weak_labels(feature_df)

    if labeled.empty:
        raise ValueError("No labeled rows were created.")
    if labeled["label"].nunique() < 2:
        raise ValueError("Need both positive and negative labels.")

    X = labeled[FEATURE_COLUMNS].copy()
    y = labeled["label"].copy()

    model = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("clf", LogisticRegression(max_iter=3000, class_weight="balanced", random_state=random_state)),
        ]
    )

    if len(labeled) >= 30:
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.25, stratify=y, random_state=random_state
        )
        model.fit(X_train, y_train)
        pred = model.predict(X_test)
        proba = model.predict_proba(X_test)[:, 1]
        metrics = {
            "train_rows": int(len(X_train)),
            "test_rows": int(len(X_test)),
            "accuracy": round(float(accuracy_score(y_test, pred)), 4),
            "auc": round(float(roc_auc_score(y_test, proba)), 4),
            "positive_rate": round(float(y.mean()), 4),
        }
    else:
        model.fit(X, y)
        metrics = {
            "train_rows": int(len(X)),
            "test_rows": 0,
            "accuracy": None,
            "auc": None,
            "positive_rate": round(float(y.mean()), 4),
        }

    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, model_path)
    return model, metrics, labeled


def load_ranker(model_path: Path | str = MODEL_PATH):
    model_path = Path(model_path)
    if not model_path.exists():
        return None
    return joblib.load(model_path)


def predict_scores(model, feature_df: pd.DataFrame) -> np.ndarray:
    X = feature_df[FEATURE_COLUMNS].copy()
    return model.predict_proba(X)[:, 1]


def blend_scores(
    heuristic_scores: list[float] | np.ndarray,
    ml_scores: list[float] | np.ndarray,
    alpha: float = 0.70,
) -> np.ndarray:
    """
    alpha * ML + (1-alpha) * normalized heuristic
    """
    h = _normalize(heuristic_scores)
    m = np.asarray(ml_scores, dtype=float)
    return alpha * m + (1.0 - alpha) * h
