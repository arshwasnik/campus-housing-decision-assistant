from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parent
SRC_PATH = PROJECT_ROOT / "src"

if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from campus_housing_decision_assistant.config import (  # noqa: E402
    DEFAULT_PREFERENCES,
    FIGURES_DIR,
    PROCESSED_DATA_DIR,
    RAW_DATA_PATH,
    SCORING_SETTINGS,
)
from campus_housing_decision_assistant.pipeline import (  # noqa: E402
    clean_apartment_data,
    load_apartment_data,
    rank_apartments,
    save_dataframe,
)
from campus_housing_decision_assistant.visualization import (  # noqa: E402
    plot_rent_vs_distance,
    plot_score_breakdown,
    plot_top_apartments,
)


def print_recommendations(ranked_df, top_n: int = 5) -> None:
    """Print the top apartments and the score components behind each ranking."""
    columns_to_show = [
        "property_name",
        "rent",
        "rent_per_person",
        "commute_minutes_used",
        "space_value_score",
        "affordability_score",
        "commute_convenience_score",
        "amenity_score",
        "safety_score",
        "hidden_cost_risk_score",
        "overall_score",
    ]

    print("\nTop apartment recommendations:\n")
    print(ranked_df.loc[:, columns_to_show].head(top_n).to_string(index=False))


def main() -> None:
    """Run the full Phase 1 apartment ranking pipeline."""
    input_csv_path = RAW_DATA_PATH

    # Edit this dictionary to test different student preferences.
    student_preferences = DEFAULT_PREFERENCES.copy()

    raw_df = load_apartment_data(input_csv_path)
    cleaned_df = clean_apartment_data(raw_df)
    ranked_df = rank_apartments(cleaned_df, student_preferences, SCORING_SETTINGS)

    cleaned_output_path = PROCESSED_DATA_DIR / "cleaned_apartment_listings.csv"
    ranked_output_path = PROCESSED_DATA_DIR / "ranked_apartment_recommendations.csv"

    save_dataframe(cleaned_df, cleaned_output_path)
    save_dataframe(ranked_df, ranked_output_path)

    plot_rent_vs_distance(ranked_df, FIGURES_DIR / "rent_vs_distance.png")
    plot_top_apartments(ranked_df, FIGURES_DIR / "top_apartments_by_score.png")
    plot_score_breakdown(ranked_df, FIGURES_DIR / "top_5_score_breakdown.png")

    print(f"Loaded data from: {input_csv_path}")
    print(f"Saved cleaned data to: {cleaned_output_path}")
    print(f"Saved ranked results to: {ranked_output_path}")
    print(f"Saved figures to: {FIGURES_DIR}")
    print("\nStudent preferences:")
    for key, value in student_preferences.items():
        print(f"  - {key}: {value}")

    print_recommendations(ranked_df, top_n=5)


if __name__ == "__main__":
    main()
