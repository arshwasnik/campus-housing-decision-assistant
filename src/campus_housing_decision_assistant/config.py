from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DATA_PATH = PROJECT_ROOT / "data" / "raw" / "sample_apartments.csv"
PROCESSED_DATA_DIR = PROJECT_ROOT / "data" / "processed"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
FIGURES_DIR = OUTPUTS_DIR / "figures"


DEFAULT_PREFERENCES = {
    "max_rent": 900,
    "max_commute_minutes": 15,
    "roommate_count": 1,
    "priority_budget": 0.35,
    "priority_commute": 0.25,
    "priority_space": 0.15,
    "priority_bathrooms": 0.15,
    "priority_amenities": 0.10,
}


SCORING_SETTINGS = {
    "campus_name": "Sample State University",
    "campus_latitude": 30.2849,
    "campus_longitude": -97.7341,
    "average_commute_speed_mph": 18,
    "space_score_floor": 120,
    "space_score_ceiling": 350,
    "bathroom_ratio_floor": 0.25,
    "bathroom_ratio_ceiling": 0.75,
    "hidden_cost_penalty_weight": 0.15,
}


AMENITY_KEYWORDS = {
    "laundry": ["laundry", "washer", "dryer", "washer/dryer"],
    "parking": ["parking", "garage", "bike storage"],
    "furnished": ["furnished"],
    "gym": ["gym", "fitness center"],
    "study_space": ["study", "study room", "study lounge"],
    "internet": ["internet", "wi-fi", "wifi"],
    "utilities_included": ["utilities included", "all utilities", "water included"],
}


HIDDEN_COST_KEYWORDS = {
    "utilities_extra": ["utilities not included", "tenant pays", "pays electricity", "pays gas"],
    "application_fee": ["application fee", "admin fee"],
    "parking_fee": ["parking fee", "reserved parking", "parking fee applies"],
    "pet_fee": ["pet fee"],
    "deposit": ["deposit"],
}
