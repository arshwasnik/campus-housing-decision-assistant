from __future__ import annotations

from typing import Any

import pandas as pd


SCORE_LABELS = {
    "affordability": "affordability",
    "commute": "commute convenience",
    "space": "space and value",
    "amenities": "amenities",
    "safety": "safety",
    "hidden_cost": "low hidden-cost risk",
}


PRIORITY_SCORE_COLUMNS = {
    "affordability": "affordability_score",
    "commute": "commute_convenience_score",
    "space": "space_value_score",
    "amenities": "amenity_score",
    "safety": "safety_score",
    "hidden_cost": "hidden_cost_score",
}


def format_currency(value: float) -> str:
    """Format numeric values as rounded US dollar amounts."""
    return f"${value:,.0f}"


def humanize_label(value: str) -> str:
    """Convert internal snake_case labels into readable text."""
    return value.replace("_", " ")


def split_list_text(value: str) -> list[str]:
    """Split comma-separated amenity summaries into normalized tokens."""
    text = str(value).strip()
    if not text or text.lower() == "none":
        return []
    return [item.strip() for item in text.split(",") if item.strip()]


def format_hidden_cost_flags(value: str) -> str:
    """Rewrite hidden cost flags into more natural tradeoff language."""
    replacements = {
        "utilities extra": "utilities are extra",
        "parking separate": "parking is separate",
        "laundry separate": "laundry is separate",
    }
    flags = split_list_text(value)
    formatted_flags = [replacements.get(flag, flag) for flag in flags]
    return join_phrases(formatted_flags)


def join_phrases(items: list[str]) -> str:
    """Join short phrases into a natural-sounding English list."""
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return f"{', '.join(items[:-1])}, and {items[-1]}"


def choose_active_preferences(preferences: dict[str, Any], parsed_preferences: dict[str, Any] | None) -> dict[str, Any]:
    """Use explicitly parsed user preferences when available, otherwise fall back to pipeline defaults."""
    if parsed_preferences is None:
        return {
            "max_rent": preferences.get("max_rent"),
            "max_commute_minutes": preferences.get("max_commute_minutes"),
            "desired_bedrooms": preferences.get("desired_bedrooms"),
            "required_amenities": preferences.get("required_amenities", []),
            "weights": {
                "affordability": preferences.get("priority_affordability", 0),
                "commute": preferences.get("priority_commute", 0),
                "space": preferences.get("priority_space_value", 0),
                "amenities": preferences.get("priority_amenities", 0),
                "safety": preferences.get("priority_safety", 0),
                "hidden_cost": preferences.get("priority_hidden_cost", 0),
            },
        }

    return {
        "max_rent": parsed_preferences.get("max_rent"),
        "max_commute_minutes": parsed_preferences.get("max_commute_minutes"),
        "desired_bedrooms": parsed_preferences.get("desired_bedrooms"),
        "required_amenities": parsed_preferences.get("required_amenities", []),
        "weights": parsed_preferences.get("weights", {}),
    }


def build_preference_match_phrases(row: pd.Series, active_preferences: dict[str, Any]) -> list[str]:
    """Describe which explicit user preferences a listing satisfies."""
    match_phrases = []

    max_rent = active_preferences.get("max_rent")
    if max_rent is not None and row["rent_per_person"] <= max_rent:
        match_phrases.append(
            f"stays within your budget target at about {format_currency(row['rent_per_person'])} per person"
        )

    max_commute_minutes = active_preferences.get("max_commute_minutes")
    if max_commute_minutes is not None and row["commute_minutes_used"] <= max_commute_minutes:
        match_phrases.append(
            f"meets your commute target with an estimated {row['commute_minutes_used']:.0f}-minute trip"
        )

    desired_bedrooms = active_preferences.get("desired_bedrooms")
    if desired_bedrooms is not None and row["bedrooms"] >= desired_bedrooms:
        bedroom_count = int(row["bedrooms"])
        if bedroom_count == desired_bedrooms:
            match_phrases.append(f"matches your request for {desired_bedrooms} bedrooms")
        else:
            match_phrases.append(
                f"meets your bedroom target with {bedroom_count} bedrooms"
            )

    required_amenities = active_preferences.get("required_amenities", [])
    missing_amenities = set(split_list_text(row["missing_required_amenities"]))
    matched_amenities = [
        humanize_label(amenity)
        for amenity in required_amenities
        if amenity not in missing_amenities
    ]
    if matched_amenities and len(matched_amenities) == len(required_amenities):
        match_phrases.append(f"includes your requested {join_phrases(matched_amenities)}")
    elif matched_amenities:
        match_phrases.append(
            f"covers some of your requested amenities, including {join_phrases(matched_amenities)}"
        )

    return match_phrases


def describe_strength(column_name: str, row: pd.Series) -> str:
    """Turn a strong component score into a short, concrete explanation."""
    if column_name == "affordability_score":
        return f"affordability, with rent around {format_currency(row['rent_per_person'])} per person"
    if column_name == "commute_convenience_score":
        return (
            f"commute convenience, with about {row['commute_minutes_used']:.0f} minutes to campus "
            f"and {row['walkability_score']:.0f} walkability"
        )
    if column_name == "space_value_score":
        return (
            f"space and value, with about {row['space_per_person']:.0f} square feet per person"
        )
    if column_name == "amenity_score":
        matched_amenities = split_list_text(row["matched_amenities"])
        if matched_amenities:
            return f"amenities like {join_phrases(matched_amenities[:3])}"
        return "its amenity package"
    if column_name == "safety_score":
        return f"safety, with a {row['safety_rating']:.1f}/5 rating"
    if column_name == "hidden_cost_score":
        hidden_cost_flags = str(row["hidden_cost_flags"]).strip().lower()
        if hidden_cost_flags == "none":
            return "low hidden-cost risk"
        return "manageable hidden-cost risk compared with other listings"
    return "balanced overall performance"


def build_strength_phrases(row: pd.Series) -> list[str]:
    """Select the strongest score components for a listing."""
    score_columns = [
        "affordability_score",
        "commute_convenience_score",
        "space_value_score",
        "amenity_score",
        "safety_score",
        "hidden_cost_score",
    ]
    ranked_strengths = sorted(score_columns, key=lambda column: float(row[column]), reverse=True)
    highlighted_columns = [column for column in ranked_strengths if row[column] >= 75][:3]

    if not highlighted_columns:
        highlighted_columns = ranked_strengths[:2]

    return [describe_strength(column_name, row) for column_name in highlighted_columns]


def describe_priority_alignment(row: pd.Series, active_preferences: dict[str, Any]) -> str | None:
    """Highlight when a listing performs well on the user's most important categories."""
    weight_map = active_preferences.get("weights", {})
    if not weight_map:
        return None

    top_categories = sorted(weight_map, key=weight_map.get, reverse=True)[:2]
    aligned_categories = [
        SCORE_LABELS[category]
        for category in top_categories
        if row[PRIORITY_SCORE_COLUMNS[category]] >= 70
    ]
    if not aligned_categories:
        return None

    return join_phrases(aligned_categories)


def choose_tradeoff(row: pd.Series, active_preferences: dict[str, Any]) -> str | None:
    """Pick one relevant tradeoff for the listing."""
    missing_amenities = [humanize_label(item) for item in split_list_text(row["missing_required_amenities"])]
    if missing_amenities:
        return f"it misses your requested {join_phrases(missing_amenities)}"

    desired_bedrooms = active_preferences.get("desired_bedrooms")
    if desired_bedrooms is not None and row["bedrooms"] < desired_bedrooms:
        return f"it falls short of your bedroom target with {int(row['bedrooms'])} bedrooms"

    max_rent = active_preferences.get("max_rent")
    if max_rent is not None and row["rent_per_person"] > max_rent:
        return f"rent per person is above your target at about {format_currency(row['rent_per_person'])}"

    max_commute_minutes = active_preferences.get("max_commute_minutes")
    if max_commute_minutes is not None and row["commute_minutes_used"] > max_commute_minutes:
        return f"the commute is longer than your target at about {row['commute_minutes_used']:.0f} minutes"

    if row["hidden_fees_estimate"] >= 200:
        return f"estimated hidden fees are on the higher side at about {format_currency(row['hidden_fees_estimate'])}"

    if row["space_value_score"] < 60:
        return "it offers less space for the price than the strongest alternatives"

    if row["safety_score"] < 65:
        return "its safety and walkability profile is weaker than the top options"

    hidden_cost_flags = str(row["hidden_cost_flags"]).strip().lower()
    if hidden_cost_flags and hidden_cost_flags != "none":
        return f"some extra costs are not bundled, especially {format_hidden_cost_flags(hidden_cost_flags)}"

    return None


def generate_recommendation_explanation(
    row: pd.Series,
    preferences: dict[str, Any],
    parsed_preferences: dict[str, Any] | None = None,
) -> str:
    """Generate a plain-English explanation for one ranked apartment listing."""
    active_preferences = choose_active_preferences(preferences, parsed_preferences)
    match_phrases = build_preference_match_phrases(row, active_preferences)
    strength_phrases = build_strength_phrases(row)
    priority_alignment = describe_priority_alignment(row, active_preferences)
    tradeoff = choose_tradeoff(row, active_preferences)

    sentences = []
    property_name = row["property_name"]

    if match_phrases:
        sentences.append(f"{property_name} ranks highly because it {join_phrases(match_phrases[:3])}.")
    else:
        sentences.append(f"{property_name} ranks highly because it performs well across several weighted factors.")

    sentences.append(f"Its strongest factors are {join_phrases(strength_phrases)}.")

    if priority_alignment is not None:
        sentences.append(f"That lines up especially well with your priorities around {priority_alignment}.")

    if tradeoff is not None:
        sentences.append(f"The main tradeoff is that {tradeoff}.")

    return " ".join(sentences)


def add_recommendation_explanations(
    ranked_df: pd.DataFrame,
    preferences: dict[str, Any],
    parsed_preferences: dict[str, Any] | None = None,
) -> pd.DataFrame:
    """Append a deterministic explanation column to ranked apartment results."""
    explained_df = ranked_df.copy()
    explained_df["recommendation_explanation"] = explained_df.apply(
        lambda row: generate_recommendation_explanation(
            row,
            preferences=preferences,
            parsed_preferences=parsed_preferences,
        ),
        axis=1,
    )
    return explained_df
