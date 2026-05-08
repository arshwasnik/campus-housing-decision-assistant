from __future__ import annotations

import re
from typing import Any


NUMBER_WORDS = {
    "studio": 1,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
}


AMENITY_PATTERNS = {
    "parking": ["parking", "garage", "covered parking", "bike storage"],
    "laundry": ["laundry", "washer", "dryer", "washer/dryer", "in-unit laundry"],
    "furnished": ["furnished", "furniture included"],
    "gym": ["gym", "fitness center"],
    "study_space": ["study space", "study room", "study lounge"],
    "internet": ["internet", "wi-fi", "wifi"],
    "utilities_included": ["utilities included", "all utilities", "water included"],
    "pet_friendly": ["pet friendly", "pets allowed", "cat friendly", "dog friendly"],
}


PRIORITY_KEYWORDS = {
    "affordability": ["cheap", "budget", "low rent", "affordable", "price", "rent"],
    "commute": ["commute", "close to campus", "walk to campus", "near campus", "minutes", "distance"],
    "space": ["space", "roomy", "spacious", "square feet", "bedroom", "bathroom"],
    "amenities": ["amenities", "parking", "laundry", "furnished", "gym", "wifi", "internet"],
    "safety": ["safe", "safety", "secure", "quiet", "well-lit", "well lit"],
}


DEFAULT_WEIGHT_POINTS = {
    "affordability": 35,
    "commute": 25,
    "space": 18,
    "amenities": 12,
    "safety": 10,
}


EMPHASIS_PATTERNS = [
    r"care most about (?P<clause>[^.]+)",
    r"most important(?: thing)? is (?P<clause>[^.]+)",
    r"priorit(?:ize|izing|ise|ising) (?P<clause>[^.]+)",
    r"mainly care about (?P<clause>[^.]+)",
    r"focus(?:ed)? on (?P<clause>[^.]+)",
]


def parse_preference_text(preference_text: str) -> dict[str, Any]:
    """Convert a natural language preference string into structured ranking inputs."""
    normalized_text = normalize_text(preference_text)

    parsed_preferences = {
        "max_rent": parse_max_rent(normalized_text),
        "max_commute_minutes": parse_max_commute_minutes(normalized_text),
        "desired_bedrooms": parse_desired_bedrooms(normalized_text),
        "required_amenities": parse_required_amenities(normalized_text),
    }
    parsed_preferences["weights"] = infer_priority_weights(normalized_text)
    return parsed_preferences


def build_pipeline_preferences(parsed_preferences: dict[str, Any], default_preferences: dict[str, Any]) -> dict[str, Any]:
    """Merge parsed preferences into the flat preference dictionary used by the ranking pipeline."""
    pipeline_preferences = default_preferences.copy()

    if parsed_preferences.get("max_rent") is not None:
        pipeline_preferences["max_rent"] = parsed_preferences["max_rent"]

    if parsed_preferences.get("max_commute_minutes") is not None:
        pipeline_preferences["max_commute_minutes"] = parsed_preferences["max_commute_minutes"]

    if parsed_preferences.get("desired_bedrooms") is not None:
        pipeline_preferences["desired_bedrooms"] = parsed_preferences["desired_bedrooms"]

    if parsed_preferences.get("required_amenities"):
        pipeline_preferences["required_amenities"] = parsed_preferences["required_amenities"]

    parsed_weights = parsed_preferences.get("weights", {})
    if parsed_weights:
        pipeline_preferences["priority_affordability"] = parsed_weights["affordability"]
        pipeline_preferences["priority_commute"] = parsed_weights["commute"]
        pipeline_preferences["priority_space_value"] = parsed_weights["space"]
        pipeline_preferences["priority_amenities"] = parsed_weights["amenities"]
        pipeline_preferences["priority_safety"] = parsed_weights["safety"]

    return pipeline_preferences


def normalize_text(preference_text: str) -> str:
    """Lowercase and collapse whitespace so simple regex rules work more consistently."""
    collapsed = " ".join(preference_text.lower().strip().split())
    return collapsed.replace("-", " ")


def parse_max_rent(normalized_text: str) -> int | None:
    """Extract a monthly rent ceiling like 'under $850' or '$900 per month'."""
    rent_patterns = [
        r"(?:under|below|less than|no more than|up to|max(?:imum)?(?: rent)?(?: of)?)\s*\$?\s*(\d{3,4})",
        r"\$?\s*(\d{3,4})\s*(?:per month|/ month|/mo|a month|monthly)\b",
    ]

    for pattern in rent_patterns:
        match = re.search(pattern, normalized_text)
        if match:
            return int(match.group(1))

    return None


def parse_max_commute_minutes(normalized_text: str) -> int | None:
    """Extract a commute ceiling like 'within 15 minutes of campus'."""
    commute_patterns = [
        r"(?:within|under|less than|no more than|up to|max(?:imum)?(?: commute)?(?: of)?)\s*(\d{1,2})\s*(?:minutes|minute|min)\b",
        r"(\d{1,2})\s*(?:minutes|minute|min)\s*(?:from|to|of)?\s*(?:campus|school|class)\b",
    ]

    for pattern in commute_patterns:
        match = re.search(pattern, normalized_text)
        if match:
            return int(match.group(1))

    return None


def parse_desired_bedrooms(normalized_text: str) -> int | None:
    """Extract a preferred bedroom count like '2 bedrooms' or 'studio'."""
    bedroom_match = re.search(
        r"\b(studio|one|two|three|four|five|six|\d+)\s*(?:bed|beds|bedroom|bedrooms|br)\b",
        normalized_text,
    )
    if bedroom_match:
        return convert_number_token(bedroom_match.group(1))

    if "studio" in normalized_text:
        return 1

    return None


def parse_required_amenities(normalized_text: str) -> list[str]:
    """Collect amenities explicitly mentioned in the user's request."""
    required_amenities = []

    for amenity, phrases in AMENITY_PATTERNS.items():
        if any(phrase in normalized_text for phrase in phrases):
            required_amenities.append(amenity)

    return required_amenities


def infer_priority_weights(normalized_text: str) -> dict[str, float]:
    """Turn rough language cues into normalized scoring weights."""
    weight_points = DEFAULT_WEIGHT_POINTS.copy()

    for category, keywords in PRIORITY_KEYWORDS.items():
        mention_count = sum(1 for keyword in keywords if keyword in normalized_text)
        weight_points[category] += mention_count * 4

    for pattern in EMPHASIS_PATTERNS:
        match = re.search(pattern, normalized_text)
        if not match:
            continue

        emphasis_clause = match.group("clause")
        for category, keywords in PRIORITY_KEYWORDS.items():
            if any(keyword in emphasis_clause for keyword in keywords):
                weight_points[category] += 10

    return normalize_weight_points(weight_points)


def normalize_weight_points(weight_points: dict[str, float]) -> dict[str, float]:
    """Convert raw weight points into decimals that sum to 1.0."""
    total_points = sum(weight_points.values())
    if total_points <= 0:
        equal_weight = 1 / len(weight_points)
        return {category: round(equal_weight, 2) for category in weight_points}

    normalized_weights = {
        category: value / total_points for category, value in weight_points.items()
    }

    rounded_weights = {
        category: round(value, 2)
        for category, value in normalized_weights.items()
    }

    # Small rounding adjustments can push the total away from exactly 1.0.
    difference = round(1.0 - sum(rounded_weights.values()), 2)
    if difference != 0:
        largest_category = max(rounded_weights, key=rounded_weights.get)
        rounded_weights[largest_category] = round(rounded_weights[largest_category] + difference, 2)

    return rounded_weights


def convert_number_token(token: str) -> int:
    """Convert either 'two' or '2' into an integer bedroom count."""
    stripped_token = token.strip().lower()
    if stripped_token.isdigit():
        return int(stripped_token)
    return NUMBER_WORDS[stripped_token]
