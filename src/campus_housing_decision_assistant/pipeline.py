from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd


NUMERIC_COLUMNS = [
    "rent",
    "bedrooms",
    "bathrooms",
    "square_feet",
    "latitude",
    "longitude",
    "distance_to_campus_miles",
    "commute_time_minutes",
    "safety_rating",
    "walkability_score",
    "lease_length_months",
    "hidden_fees_estimate",
]


BOOLEAN_COLUMNS = [
    "parking_included",
    "laundry_included",
    "utilities_included",
    "furnished",
    "pet_friendly",
]


TEXT_COLUMNS = ["city", "state", "description"]


COLUMN_ALIASES = {
    "square_footage": "square_feet",
    "distance_to_campus": "distance_to_campus_miles",
    "distance_to_campus_mi": "distance_to_campus_miles",
    "commute_time": "commute_time_minutes",
    "commute_minutes": "commute_time_minutes",
    "parking_included_": "parking_included",
    "laundry_included_": "laundry_included",
    "utilities_included_": "utilities_included",
    "lease_length": "lease_length_months",
    "lease_length_month": "lease_length_months",
    "hidden_fees": "hidden_fees_estimate",
    "hidden_fee_estimate": "hidden_fees_estimate",
}


AMENITY_LABELS = {
    "parking_included": "parking",
    "laundry_included": "laundry",
    "utilities_included": "utilities",
    "furnished": "furnished",
    "pet_friendly": "pet friendly",
}


REQUIRED_AMENITY_COLUMN_MAP = {
    "parking": "parking_included",
    "laundry": "laundry_included",
    "utilities_included": "utilities_included",
    "furnished": "furnished",
    "pet_friendly": "pet_friendly",
}


DESCRIPTION_AMENITY_KEYWORDS = {
    "parking": ["parking", "garage", "bike storage"],
    "laundry": ["laundry", "washer", "dryer", "washer/dryer"],
    "utilities_included": ["utilities included", "all utilities", "water included"],
    "furnished": ["furnished"],
    "pet_friendly": ["pet friendly", "pets allowed", "cat friendly", "dog friendly"],
    "gym": ["gym", "fitness center"],
    "study_space": ["study", "study room", "study lounge"],
    "internet": ["internet", "wi-fi", "wifi"],
}


TRUE_VALUES = {"true", "yes", "y", "1", "included", "free", "covered", "available"}
FALSE_VALUES = {"false", "no", "n", "0", "not included", "none", "street", "paid", "extra"}


def load_apartment_data(csv_path: Path | str) -> pd.DataFrame:
    """Load apartment listings from a CSV file."""
    return pd.read_csv(csv_path)


def normalize_column_name(column_name: str) -> str:
    """Convert column names to a predictable snake_case schema."""
    normalized = re.sub(r"[^a-z0-9]+", "_", str(column_name).strip().lower()).strip("_")
    return COLUMN_ALIASES.get(normalized, normalized)


def standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Rename incoming columns so the rest of the pipeline can use a stable schema."""
    rename_map = {column: normalize_column_name(column) for column in df.columns}
    return df.rename(columns=rename_map)


def clean_numeric_series(series: pd.Series) -> pd.Series:
    """Strip common text like '$', 'sqft', 'mi', and 'bd' before converting to numbers."""
    cleaned = (
        series.astype(str)
        .str.replace("studio", "1", case=False, regex=False)
        .str.replace(",", "", regex=False)
        .str.replace(r"[^0-9.\-]", "", regex=True)
        .replace({"": np.nan, "nan": np.nan, "None": np.nan})
    )
    return pd.to_numeric(cleaned, errors="coerce")


def clean_boolean_series(series: pd.Series) -> pd.Series:
    """Normalize yes/no style text into boolean values."""
    normalized = series.fillna("").astype(str).str.strip().str.lower()
    cleaned = np.where(
        normalized.isin(TRUE_VALUES),
        True,
        np.where(normalized.isin(FALSE_VALUES), False, np.nan),
    )
    return pd.Series(cleaned, index=series.index)


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


def clean_apartment_data(df: pd.DataFrame) -> pd.DataFrame:
    """Clean numeric, boolean, and text columns so the dataset is ready for scoring."""
    cleaned_df = standardize_columns(df.copy())

    for column in NUMERIC_COLUMNS:
        if column not in cleaned_df.columns:
            cleaned_df[column] = np.nan

    for column in BOOLEAN_COLUMNS:
        if column not in cleaned_df.columns:
            cleaned_df[column] = np.nan

    for column in TEXT_COLUMNS:
        if column not in cleaned_df.columns:
            cleaned_df[column] = ""

    for column in NUMERIC_COLUMNS:
        cleaned_df[column] = clean_numeric_series(cleaned_df[column])

    for column in BOOLEAN_COLUMNS:
        cleaned_df[column] = clean_boolean_series(cleaned_df[column]).fillna(False).astype(bool)

    cleaned_df["city"] = cleaned_df["city"].fillna("").astype(str).str.strip().str.title()
    cleaned_df["state"] = cleaned_df["state"].fillna("").astype(str).str.strip().str.upper()
    cleaned_df["description"] = cleaned_df["description"].fillna("").astype(str).str.strip()

    median_fill_columns = [
        "rent",
        "bedrooms",
        "bathrooms",
        "square_feet",
        "latitude",
        "longitude",
        "safety_rating",
        "walkability_score",
        "lease_length_months",
        "hidden_fees_estimate",
    ]
    for column in median_fill_columns:
        fill_value = cleaned_df[column].median()
        cleaned_df[column] = cleaned_df[column].fillna(0 if pd.isna(fill_value) else fill_value)

    cleaned_df["listing_id"] = pd.to_numeric(
        cleaned_df.get("listing_id", pd.Series(np.arange(1, len(cleaned_df) + 1))),
        errors="coerce",
    ).fillna(pd.Series(np.arange(1, len(cleaned_df) + 1)))
    cleaned_df["property_name"] = (
        cleaned_df.get("property_name", pd.Series(["Unknown Listing"] * len(cleaned_df)))
        .fillna("Unknown Listing")
        .astype(str)
        .str.strip()
    )

    cleaned_df["bedrooms"] = cleaned_df["bedrooms"].clip(lower=1)
    cleaned_df["bathrooms"] = cleaned_df["bathrooms"].clip(lower=0.5)
    cleaned_df["square_feet"] = cleaned_df["square_feet"].clip(lower=250)
    cleaned_df["distance_to_campus_miles"] = cleaned_df["distance_to_campus_miles"].clip(lower=0)
    cleaned_df["commute_time_minutes"] = cleaned_df["commute_time_minutes"].clip(lower=0)
    cleaned_df["safety_rating"] = cleaned_df["safety_rating"].clip(lower=1, upper=5)
    cleaned_df["walkability_score"] = cleaned_df["walkability_score"].clip(lower=0, upper=100)
    cleaned_df["lease_length_months"] = cleaned_df["lease_length_months"].clip(lower=6, upper=18)
    cleaned_df["hidden_fees_estimate"] = cleaned_df["hidden_fees_estimate"].clip(lower=0)

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


def normalize_priority_weights(preferences: dict) -> dict:
    """Scale user priorities so the ranking weights add up to 1."""
    weights = {
        "affordability": preferences["priority_affordability"],
        "commute": preferences["priority_commute"],
        "space_value": preferences["priority_space_value"],
        "amenities": preferences["priority_amenities"],
        "safety": preferences["priority_safety"],
        "hidden_cost": preferences["priority_hidden_cost"],
    }

    total_weight = sum(weights.values())
    if total_weight <= 0:
        equal_weight = 1 / len(weights)
        return {name: equal_weight for name in weights}

    return {name: value / total_weight for name, value in weights.items()}


def summarize_amenities(row: pd.Series) -> str:
    """List the amenities that are explicitly included for a listing."""
    matched = [label for column, label in AMENITY_LABELS.items() if bool(row[column])]
    return ", ".join(matched) if matched else "none"


def summarize_hidden_cost_flags(row: pd.Series) -> str:
    """List the main reasons a listing may carry extra monthly or move-in costs."""
    flags = []
    if row["hidden_fees_estimate"] >= 250:
        flags.append("high upfront fees")
    elif row["hidden_fees_estimate"] >= 125:
        flags.append("moderate upfront fees")

    if not row["utilities_included"]:
        flags.append("utilities extra")
    if not row["parking_included"]:
        flags.append("parking separate")
    if not row["laundry_included"]:
        flags.append("laundry separate")

    return ", ".join(flags) if flags else "none"


def score_bedroom_preference(bedrooms: pd.Series, desired_bedrooms: int | None) -> pd.Series:
    """Reward matches to a requested bedroom count without overpowering the main space/value score."""
    if desired_bedrooms is None:
        return pd.Series(100.0, index=bedrooms.index)

    difference = bedrooms - desired_bedrooms
    scores = np.where(difference >= 0, 100 - (difference * 15), 100 - (np.abs(difference) * 35))
    return pd.Series(np.clip(scores, 0, 100), index=bedrooms.index)


def score_required_amenities(df: pd.DataFrame, required_amenities: list[str]) -> pd.Series:
    """Score required amenities using explicit columns first and description fallback when needed."""
    if not required_amenities:
        return pd.Series(100.0, index=df.index)

    matched_counts = pd.Series(0.0, index=df.index)

    for amenity in required_amenities:
        column_name = REQUIRED_AMENITY_COLUMN_MAP.get(amenity)
        if column_name is not None:
            matched_counts += df[column_name].astype(float)
            continue

        keywords = DESCRIPTION_AMENITY_KEYWORDS.get(amenity, [amenity.replace("_", " ")])
        matched_counts += df["description"].str.lower().apply(
            lambda text: float(any(keyword in text for keyword in keywords))
        )

    return 100 * matched_counts / len(required_amenities)


def summarize_missing_required_amenities(row: pd.Series, required_amenities: list[str]) -> str:
    """Show which requested amenities a listing does not satisfy."""
    if not required_amenities:
        return "none"

    missing = []
    description_text = str(row["description"]).lower()
    for amenity in required_amenities:
        column_name = REQUIRED_AMENITY_COLUMN_MAP.get(amenity)
        if column_name is not None and bool(row[column_name]):
            continue

        keywords = DESCRIPTION_AMENITY_KEYWORDS.get(amenity, [amenity.replace("_", " ")])
        if any(keyword in description_text for keyword in keywords):
            continue

        missing.append(amenity)

    return ", ".join(missing) if missing else "none"


def engineer_features(df: pd.DataFrame, preferences: dict, settings: dict) -> pd.DataFrame:
    """Create transparent comparison features used by the ranking algorithm."""
    featured_df = df.copy()
    roommate_count = max(int(preferences.get("roommate_count", 1)), 0)
    total_people = roommate_count + 1
    desired_bedrooms = preferences.get("desired_bedrooms")
    required_amenities = preferences.get("required_amenities", [])

    featured_df["distance_to_campus_miles"] = featured_df["distance_to_campus_miles"].fillna(
        haversine_distance_miles(
            featured_df["latitude"],
            featured_df["longitude"],
            settings["campus_latitude"],
            settings["campus_longitude"],
        )
    )

    estimated_commute = featured_df["distance_to_campus_miles"] / settings["average_commute_speed_mph"] * 60
    featured_df["commute_minutes_used"] = featured_df["commute_time_minutes"].fillna(estimated_commute)

    featured_df["total_people"] = total_people
    featured_df["rent_per_person"] = featured_df["rent"] / total_people
    featured_df["rent_per_bedroom"] = featured_df["rent"] / featured_df["bedrooms"].clip(lower=1)
    featured_df["rent_per_square_foot"] = featured_df["rent"] / featured_df["square_feet"].replace(0, np.nan)
    featured_df["bathroom_ratio"] = featured_df["bathrooms"] / total_people
    featured_df["space_per_person"] = featured_df["square_feet"] / total_people
    featured_df["bedroom_share"] = featured_df["bedrooms"] / total_people
    featured_df["hidden_fees_monthly"] = (
        featured_df["hidden_fees_estimate"] / featured_df["lease_length_months"].replace(0, np.nan)
    )
    featured_df["hidden_fees_monthly_per_person"] = featured_df["hidden_fees_monthly"] / total_people
    featured_df["effective_monthly_cost_per_person"] = (
        featured_df["rent_per_person"] + featured_df["hidden_fees_monthly_per_person"]
    )

    featured_df["affordability_score"] = linear_score_lower_is_better(
        featured_df["rent_per_person"],
        target=preferences["max_rent"],
        cutoff_multiplier=1.6,
    )

    featured_df["commute_time_score"] = linear_score_lower_is_better(
        featured_df["commute_minutes_used"],
        target=preferences["max_commute_minutes"],
        cutoff_multiplier=2.0,
    )
    featured_df["commute_convenience_score"] = (
        0.75 * featured_df["commute_time_score"] + 0.25 * featured_df["walkability_score"]
    )

    featured_df["space_score"] = linear_score_higher_is_better(
        featured_df["space_per_person"],
        floor=settings["space_score_floor"],
        ceiling=settings["space_score_ceiling"],
    )
    featured_df["value_score"] = linear_score_lower_is_better(
        featured_df["rent_per_square_foot"],
        target=settings["value_price_target"],
        cutoff_multiplier=settings["value_price_cutoff_multiplier"],
    )
    featured_df["bathroom_score"] = linear_score_higher_is_better(
        featured_df["bathroom_ratio"],
        floor=settings["bathroom_ratio_floor"],
        ceiling=settings["bathroom_ratio_ceiling"],
    )
    featured_df["bedroom_fit_score"] = linear_score_higher_is_better(
        featured_df["bedroom_share"],
        floor=settings["bedroom_fit_floor"],
        ceiling=settings["bedroom_fit_ceiling"],
    )
    featured_df["bedroom_preference_score"] = score_bedroom_preference(
        featured_df["bedrooms"],
        desired_bedrooms=desired_bedrooms,
    )
    featured_df["space_value_score"] = (
        0.35 * featured_df["space_score"]
        + 0.25 * featured_df["value_score"]
        + 0.20 * featured_df["bathroom_score"]
        + 0.10 * featured_df["bedroom_fit_score"]
        + 0.10 * featured_df["bedroom_preference_score"]
    )

    amenity_weights = settings["amenity_weights"]
    featured_df["matched_amenities"] = featured_df.apply(summarize_amenities, axis=1)
    featured_df["base_amenity_score"] = 100 * sum(
        weight * featured_df[column].astype(int)
        for column, weight in amenity_weights.items()
    )
    featured_df["required_amenity_match_score"] = score_required_amenities(
        featured_df,
        required_amenities=required_amenities,
    )
    featured_df["missing_required_amenities"] = featured_df.apply(
        lambda row: summarize_missing_required_amenities(row, required_amenities),
        axis=1,
    )
    if required_amenities:
        featured_df["amenity_score"] = (
            0.70 * featured_df["base_amenity_score"]
            + 0.30 * featured_df["required_amenity_match_score"]
        )
    else:
        featured_df["amenity_score"] = featured_df["base_amenity_score"]

    featured_df["safety_rating_score"] = linear_score_higher_is_better(
        featured_df["safety_rating"],
        floor=settings["safety_rating_floor"],
        ceiling=settings["safety_rating_ceiling"],
    )
    featured_df["safety_score"] = (
        0.85 * featured_df["safety_rating_score"] + 0.15 * featured_df["walkability_score"]
    )

    exposure_weights = settings["hidden_cost_exposure_weights"]
    featured_df["extra_cost_exposure_score"] = 100 * sum(
        weight * (~featured_df[column]).astype(int)
        for column, weight in exposure_weights.items()
    )
    featured_df["hidden_fee_burden_score"] = linear_score_higher_is_better(
        featured_df["hidden_fees_monthly_per_person"],
        floor=0,
        ceiling=settings["hidden_fee_monthly_ceiling_per_person"],
    )
    featured_df["hidden_cost_flags"] = featured_df.apply(summarize_hidden_cost_flags, axis=1)
    featured_df["hidden_cost_risk_score"] = (
        0.70 * featured_df["hidden_fee_burden_score"]
        + 0.30 * featured_df["extra_cost_exposure_score"]
    )
    featured_df["hidden_cost_score"] = 100 - featured_df["hidden_cost_risk_score"]

    numeric_columns = featured_df.select_dtypes(include=[np.number]).columns
    featured_df[numeric_columns] = featured_df[numeric_columns].fillna(0)

    return featured_df


def rank_apartments(df: pd.DataFrame, preferences: dict, settings: dict) -> pd.DataFrame:
    """Apply the weighted scoring system and sort apartments from best to worst."""
    ranked_df = engineer_features(df, preferences, settings)
    weights = normalize_priority_weights(preferences)

    ranked_df["overall_score"] = (
        weights["affordability"] * ranked_df["affordability_score"]
        + weights["commute"] * ranked_df["commute_convenience_score"]
        + weights["space_value"] * ranked_df["space_value_score"]
        + weights["amenities"] * ranked_df["amenity_score"]
        + weights["safety"] * ranked_df["safety_score"]
        + weights["hidden_cost"] * ranked_df["hidden_cost_score"]
    )

    ranked_df["overall_score"] = ranked_df["overall_score"].clip(lower=0, upper=100).round(2)

    score_columns = [
        "rent_per_person",
        "rent_per_bedroom",
        "rent_per_square_foot",
        "bathroom_ratio",
        "space_per_person",
        "distance_to_campus_miles",
        "commute_minutes_used",
        "hidden_fees_monthly_per_person",
        "effective_monthly_cost_per_person",
        "affordability_score",
        "commute_time_score",
        "commute_convenience_score",
        "space_score",
        "value_score",
        "bathroom_score",
        "bedroom_fit_score",
        "bedroom_preference_score",
        "space_value_score",
        "base_amenity_score",
        "required_amenity_match_score",
        "amenity_score",
        "safety_rating_score",
        "safety_score",
        "extra_cost_exposure_score",
        "hidden_fee_burden_score",
        "hidden_cost_risk_score",
        "hidden_cost_score",
    ]
    ranked_df[score_columns] = ranked_df[score_columns].round(2)

    return ranked_df.sort_values(by="overall_score", ascending=False).reset_index(drop=True)


def save_dataframe(df: pd.DataFrame, output_path: Path | str) -> None:
    """Save a DataFrame to CSV without the index column."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
