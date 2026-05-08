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
from campus_housing_decision_assistant.preference_parser import (  # noqa: E402
    build_pipeline_preferences,
    parse_preference_text,
)
from campus_housing_decision_assistant.visualization import (  # noqa: E402
    plot_rent_vs_distance,
    plot_score_breakdown,
    plot_top_apartments,
)


EXAMPLE_PREFERENCE_TEXT = (
    "I want something under $850 per month, within 15 minutes of campus, "
    "with parking and laundry. I care most about low rent, commute time, "
    "and avoiding hidden fees."
)


def build_student_preferences(preference_text: str | None) -> tuple[dict, dict | None]:
    """Return pipeline-ready preferences, optionally parsed from a natural language request."""
    if not preference_text:
        return DEFAULT_PREFERENCES.copy(), None

    parsed_preferences = parse_preference_text(preference_text)
    student_preferences = build_pipeline_preferences(parsed_preferences, DEFAULT_PREFERENCES)
    return student_preferences, parsed_preferences


def print_recommendations(ranked_df, top_n: int = 3) -> None:
    """Print a compact ranking summary for the best listings."""
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
        "hidden_cost_score",
        "overall_score",
    ]

    print(f"\nTop {top_n} apartment recommendations:\n")
    print(ranked_df.loc[:, columns_to_show].head(top_n).to_string(index=False))


def main() -> None:
    """Run the apartment ranking pipeline using a natural language preference example."""
    input_csv_path = RAW_DATA_PATH
    user_preference_text = EXAMPLE_PREFERENCE_TEXT

    student_preferences, parsed_preferences = build_student_preferences(user_preference_text)

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
    print("\nOriginal preference sentence:")
    print(f"  {user_preference_text}")

    if parsed_preferences is not None:
        print("\nParsed preferences:")
        for key, value in parsed_preferences.items():
            print(f"  - {key}: {value}")

    print("\nPipeline-ready preferences:")
    for key, value in student_preferences.items():
        print(f"  - {key}: {value}")

    print_recommendations(ranked_df, top_n=3)


if __name__ == "__main__":
    main()
