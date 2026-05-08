from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, Tuple

import numpy as np
import pandas as pd

from .config import AMENITY_KEYWORDS, HIDDEN_COST_KEYWORDS


NUMERIC_COLUMNS = [
    "rent",
    "bedrooms",
    "bathrooms",
    "square_feet",
    "latitude",
    "longitude",
]


TEXT_COLUMNS = ["city", "state", "description"]


def load_apartment_data(csv_path: Path | str) -> pd.DataFrame:
    """Load apartment listings from a CSV file."""
    return pd.read_csv(csv_path)


def clean_numeric_series(series: pd.Series) -> pd.Series:
    """Strip common text like '$', 'sqft', and 'bd' before converting to numbers."""
    cleaned = (
        series.astype(str)
        .str.replace("studio", "1", case=False, regex=False)
        .str.replace(",", "", regex=False)
        .str.replace(r"[^0-9.\-]", "", regex=True)
        .replace("", np.nan)
    )
    return pd.to_numeric(cleaned, errors="coerce")


def clean_apartment_data(df: pd.DataFrame) -> pd.DataFrame:
    """Clean numeric and text columns so the dataset is ready for feature engineering."""
    cleaned_df = df.copy()

    for column in NUMERIC_COLUMNS:
        if column not in cleaned_df.columns:
            cleaned_df[column] = np.nan

    for column in NUMERIC_COLUMNS:
        cleaned_df[column] = clean_numeric_series(cleaned_df[column])

    for column in TEXT_COLUMNS:
        if column not in cleaned_df.columns:
            cleaned_df[column] = ""

    cleaned_df["city"] = cleaned_df["city"].fillna("").astype(str).str.strip().str.title()
    cleaned_df["state"] = cleaned_df["state"].fillna("").astype(str).str.strip().str.upper()
    cleaned_df["description"] = cleaned_df["description"].fillna("").astype(str).str.strip()

    numeric_fill_values = {
        "rent": cleaned_df["rent"].median(),
        "bedrooms": cleaned_df["bedrooms"].median(),
        "bathrooms": cleaned_df["bathrooms"].median(),
        "square_feet": cleaned_df["square_feet"].median(),
        "latitude": cleaned_df["latitude"].median(),
        "longitude": cleaned_df["longitude"].median(),
    }

    for column, fill_value in numeric_fill_values.items():
        cleaned_df[column] = cleaned_df[column].fillna(fill_value)

    cleaned_df["listing_id"] = cleaned_df.get("listing_id", pd.Series(range(1, len(cleaned_df) + 1)))
    cleaned_df["property_name"] = cleaned_df.get("property_name", pd.Series(["Unknown Listing"] * len(cleaned_df)))
    cleaned_df["listing_id"] = pd.to_numeric(cleaned_df["listing_id"], errors="coerce").fillna(
        pd.Series(range(1, len(cleaned_df) + 1))
    )
    cleaned_df["property_name"] = cleaned_df["property_name"].fillna("Unknown Listing").astype(str).str.strip()

    return cleaned_df


def haversine_distance_miles(
    latitudes: pd.Series,
    longitudes: pd.Series,
    campus_latitude: float,
    campus_longitude: float,
) -> pd.Series:
    """Estimate straight-line distance from each listing to campus in miles."""
    earth_radius_miles = 3958.8

    lat1 = np.radians(latitudes.astype(float))
    lon1 = np.radians(longitudes.astype(float))
    lat2 = np.radians(campus_latitude)
    lon2 = np.radians(campus_longitude)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    c = 2 * np.arcsin(np.sqrt(a))
    return earth_radius_miles * c


def linear_score_lower_is_better(value: pd.Series, target: float, cutoff_multiplier: float) -> pd.Series:
    """Return 100 at or below target, then linearly decline to 0 at the cutoff."""
    cutoff = target * cutoff_multiplier
    score = 100 * (cutoff - value) / max(cutoff - target, 1e-9)
    score = np.where(value <= target, 100, score)
    return pd.Series(np.clip(score, 0, 100), index=value.index)


def linear_score_higher_is_better(value: pd.Series, floor: float, ceiling: float) -> pd.Series:
    """Return 0 at or below the floor and 100 at or above the ceiling."""
    score = 100 * (value - floor) / max(ceiling - floor, 1e-9)
    return pd.Series(np.clip(score, 0, 100), index=value.index)


def find_keyword_matches(text: str, keyword_groups: Dict[str, Iterable[str]]) -> Tuple[list[str], int]:
    """Return matched keyword groups and how many categories were detected."""
    lowered_text = text.lower()
    matches = []

    for category, keywords in keyword_groups.items():
        if any(keyword in lowered_text for keyword in keywords):
            matches.append(category)

    return matches, len(matches)


def normalize_priority_weights(preferences: dict) -> dict:
    """Scale user priority values so the ranking weights add up to 1."""
    weights = {
        "budget": preferences["priority_budget"],
        "commute": preferences["priority_commute"],
        "space": preferences["priority_space"],
        "bathrooms": preferences["priority_bathrooms"],
        "amenities": preferences["priority_amenities"],
    }

    total_weight = sum(weights.values())
    if total_weight <= 0:
        equal_weight = 1 / len(weights)
        return {name: equal_weight for name in weights}

    return {name: value / total_weight for name, value in weights.items()}


def engineer_features(df: pd.DataFrame, preferences: dict, settings: dict) -> pd.DataFrame:
    """Create transparent comparison features used by the ranking algorithm."""
    featured_df = df.copy()
    total_people = preferences["roommate_count"] + 1
    bedroom_denominator = featured_df["bedrooms"].clip(lower=1)

    # The student is counted as one of the people sharing the apartment.
    featured_df["total_people"] = total_people
    featured_df["rent_per_person"] = featured_df["rent"] / total_people
    featured_df["rent_per_bedroom"] = featured_df["rent"] / bedroom_denominator
    featured_df["rent_per_square_foot"] = featured_df["rent"] / featured_df["square_feet"].replace(0, np.nan)
    featured_df["bathroom_ratio"] = featured_df["bathrooms"] / total_people
    featured_df["space_per_person"] = featured_df["square_feet"] / total_people
    featured_df["bedroom_fit_score"] = np.clip((featured_df["bedrooms"] / total_people) * 100, 0, 100)

    featured_df["distance_to_campus_miles"] = haversine_distance_miles(
        featured_df["latitude"],
        featured_df["longitude"],
        settings["campus_latitude"],
        settings["campus_longitude"],
    )

    featured_df["estimated_commute_minutes"] = (
        featured_df["distance_to_campus_miles"] / settings["average_commute_speed_mph"] * 60
    )

    featured_df["affordability_score"] = linear_score_lower_is_better(
        featured_df["rent_per_person"],
        target=preferences["max_rent"],
        cutoff_multiplier=1.5,
    )

    featured_df["commute_score"] = linear_score_lower_is_better(
        featured_df["estimated_commute_minutes"],
        target=preferences["max_commute_minutes"],
        cutoff_multiplier=2.0,
    )

    featured_df["space_score"] = linear_score_higher_is_better(
        featured_df["space_per_person"],
        floor=settings["space_score_floor"],
        ceiling=settings["space_score_ceiling"],
    )

    featured_df["bathroom_score"] = linear_score_higher_is_better(
        featured_df["bathroom_ratio"],
        floor=settings["bathroom_ratio_floor"],
        ceiling=settings["bathroom_ratio_ceiling"],
    )

    featured_df["comfort_score"] = (
        0.45 * featured_df["space_score"]
        + 0.35 * featured_df["bathroom_score"]
        + 0.20 * featured_df["bedroom_fit_score"]
    )

    amenity_matches = featured_df["description"].apply(
        lambda text: find_keyword_matches(text, AMENITY_KEYWORDS)
    )
    featured_df["matched_amenities"] = amenity_matches.apply(lambda result: ", ".join(result[0]) if result[0] else "none")
    featured_df["amenity_score"] = amenity_matches.apply(
        lambda result: 100 * result[1] / len(AMENITY_KEYWORDS)
    )

    hidden_cost_matches = featured_df["description"].apply(
        lambda text: find_keyword_matches(text, HIDDEN_COST_KEYWORDS)
    )
    featured_df["hidden_cost_flags"] = hidden_cost_matches.apply(
        lambda result: ", ".join(result[0]) if result[0] else "none"
    )
    featured_df["hidden_cost_risk_score"] = hidden_cost_matches.apply(
        lambda result: 100 * result[1] / len(HIDDEN_COST_KEYWORDS)
    )

    return featured_df.fillna(0)


def rank_apartments(df: pd.DataFrame, preferences: dict, settings: dict) -> pd.DataFrame:
    """Apply the weighted scoring system and sort apartments from best to worst."""
    ranked_df = engineer_features(df, preferences, settings)
    weights = normalize_priority_weights(preferences)

    ranked_df["overall_score"] = (
        weights["budget"] * ranked_df["affordability_score"]
        + weights["commute"] * ranked_df["commute_score"]
        + weights["space"] * ranked_df["space_score"]
        + weights["bathrooms"] * ranked_df["bathroom_score"]
        + weights["amenities"] * ranked_df["amenity_score"]
        # Extra fees should matter, but not dominate the whole ranking.
        - settings["hidden_cost_penalty_weight"] * ranked_df["hidden_cost_risk_score"]
    )

    ranked_df["overall_score"] = ranked_df["overall_score"].clip(lower=0, upper=100).round(2)

    score_columns = [
        "rent_per_person",
        "rent_per_bedroom",
        "rent_per_square_foot",
        "bathroom_ratio",
        "space_per_person",
        "distance_to_campus_miles",
        "estimated_commute_minutes",
        "affordability_score",
        "commute_score",
        "space_score",
        "bathroom_score",
        "comfort_score",
        "amenity_score",
        "hidden_cost_risk_score",
    ]

    ranked_df[score_columns] = ranked_df[score_columns].round(2)

    return ranked_df.sort_values(by="overall_score", ascending=False).reset_index(drop=True)


def save_dataframe(df: pd.DataFrame, output_path: Path | str) -> None:
    """Save a DataFrame to CSV without the index column."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
