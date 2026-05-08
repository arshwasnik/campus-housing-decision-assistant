from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DATA_PATH = PROJECT_ROOT / "data" / "raw" / "sample_apartments.csv"
PROCESSED_DATA_DIR = PROJECT_ROOT / "data" / "processed"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
FIGURES_DIR = OUTPUTS_DIR / "figures"


DEFAULT_PREFERENCES = {
    "max_rent": 950,
    "max_commute_minutes": 15,
    "roommate_count": 1,
    "priority_affordability": 0.30,
    "priority_commute": 0.20,
    "priority_space_value": 0.18,
    "priority_amenities": 0.14,
    "priority_safety": 0.12,
    "priority_hidden_cost": 0.06,
}


SCORING_SETTINGS = {
    "campus_name": "Sample State University",
    "campus_latitude": 30.2849,
    "campus_longitude": -97.7341,
    "average_commute_speed_mph": 18,
    "space_score_floor": 180,
    "space_score_ceiling": 550,
    "bathroom_ratio_floor": 0.40,
    "bathroom_ratio_ceiling": 1.00,
    "bedroom_fit_floor": 0.40,
    "bedroom_fit_ceiling": 1.00,
    "value_price_target": 1.90,
    "value_price_cutoff_multiplier": 2.00,
    "safety_rating_floor": 3.00,
    "safety_rating_ceiling": 4.80,
    "hidden_fee_monthly_ceiling_per_person": 35,
    "amenity_weights": {
        "parking_included": 0.15,
        "laundry_included": 0.25,
        "utilities_included": 0.30,
        "furnished": 0.20,
        "pet_friendly": 0.10,
    },
    "hidden_cost_exposure_weights": {
        "utilities_included": 0.55,
        "parking_included": 0.25,
        "laundry_included": 0.20,
    },
}
