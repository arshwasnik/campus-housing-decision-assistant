from pathlib import Path
import sys

import pandas as pd
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parent
SRC_PATH = PROJECT_ROOT / "src"

if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from campus_housing_decision_assistant.config import (  # noqa: E402
    DEFAULT_PREFERENCES,
    RAW_DATA_PATH,
    SCORING_SETTINGS,
)
from campus_housing_decision_assistant.pipeline import (  # noqa: E402
    clean_apartment_data,
    load_apartment_data,
    rank_apartments,
)
from campus_housing_decision_assistant.preference_parser import (  # noqa: E402
    build_pipeline_preferences,
    parse_preference_text,
)
from campus_housing_decision_assistant.visualization import (  # noqa: E402
    create_rent_vs_commute_figure,
)


DEFAULT_PREFERENCE_TEXT = (
    "I want something under $850 per month, within 15 minutes of campus, "
    "with parking and laundry. I care most about low rent, commute time, "
    "and avoiding hidden fees."
)


def build_ranked_recommendations(preference_text: str) -> tuple[dict, dict | None, pd.DataFrame]:
    """Parse the user's text input and return ranked apartment recommendations."""
    cleaned_text = preference_text.strip()
    parsed_preferences = None
    pipeline_preferences = DEFAULT_PREFERENCES.copy()

    if cleaned_text:
        parsed_preferences = parse_preference_text(cleaned_text)
        pipeline_preferences = build_pipeline_preferences(parsed_preferences, DEFAULT_PREFERENCES)

    raw_df = load_apartment_data(RAW_DATA_PATH)
    cleaned_df = clean_apartment_data(raw_df)
    ranked_df = rank_apartments(
        cleaned_df,
        pipeline_preferences,
        SCORING_SETTINGS,
        parsed_preferences=parsed_preferences,
    )
    return pipeline_preferences, parsed_preferences, ranked_df


def build_results_table(ranked_df: pd.DataFrame) -> pd.DataFrame:
    """Prepare a compact results table for the Streamlit UI."""
    results_df = ranked_df.loc[
        :,
        [
            "property_name",
            "overall_score",
            "rent_per_person",
            "commute_minutes_used",
            "bedrooms",
            "safety_rating",
            "matched_amenities",
            "recommendation_explanation",
        ],
    ].copy()

    results_df = results_df.rename(
        columns={
            "property_name": "Property",
            "overall_score": "Overall Score",
            "rent_per_person": "Rent Per Person",
            "commute_minutes_used": "Commute (Minutes)",
            "bedrooms": "Bedrooms",
            "safety_rating": "Safety Rating",
            "matched_amenities": "Included Amenities",
            "recommendation_explanation": "Recommendation Explanation",
        }
    )

    numeric_columns = ["Overall Score", "Rent Per Person", "Commute (Minutes)", "Bedrooms", "Safety Rating"]
    results_df[numeric_columns] = results_df[numeric_columns].round(2)
    return results_df


def render_top_recommendations(ranked_df: pd.DataFrame, top_n: int = 5) -> None:
    """Show the best listings with short metrics and recommendation explanations."""
    st.subheader("Top Recommendations")

    for rank, (_, row) in enumerate(ranked_df.head(top_n).iterrows(), start=1):
        st.markdown(f"### {rank}. {row['property_name']}")
        metric_columns = st.columns(4)
        metric_columns[0].metric("Overall Score", f"{row['overall_score']:.1f}")
        metric_columns[1].metric("Rent Per Person", f"${row['rent_per_person']:.0f}")
        metric_columns[2].metric("Commute", f"{row['commute_minutes_used']:.0f} min")
        metric_columns[3].metric("Safety", f"{row['safety_rating']:.1f}/5")
        st.write(row["recommendation_explanation"])
        st.caption(
            f"Included amenities: {row['matched_amenities']} | "
            f"Missing requested amenities: {row['missing_required_amenities']}"
        )


def main() -> None:
    """Render the final Streamlit demo for the housing decision assistant."""
    st.set_page_config(page_title="Campus Housing Decision Assistant", layout="wide")

    st.title("Campus Housing Decision Assistant")
    st.write(
        "Enter housing preferences in plain English. The app uses a rule-based parser to "
        "extract structured preferences, runs the existing explainable ranking pipeline, "
        "and returns apartment recommendations with plain-English explanations."
    )
    st.caption("This demo uses deterministic rules and does not call an LLM.")

    with st.form("preference_form"):
        preference_text = st.text_area(
            "Describe your housing preferences",
            value=DEFAULT_PREFERENCE_TEXT,
            height=130,
        )
        st.form_submit_button("Generate Recommendations")

    pipeline_preferences, parsed_preferences, ranked_df = build_ranked_recommendations(preference_text)
    top_df = ranked_df.head(5)

    details_column, table_column = st.columns([1, 2])

    with details_column:
        st.subheader("Parsed Preferences")
        if parsed_preferences is None:
            st.json({"note": "No explicit preferences detected. Using default ranking preferences."})
        else:
            st.json(parsed_preferences)

        st.subheader("Pipeline Preferences")
        st.json(pipeline_preferences)

    with table_column:
        render_top_recommendations(top_df, top_n=5)

    st.subheader("Ranked Results Table")
    st.dataframe(build_results_table(ranked_df), width="stretch", hide_index=True)

    st.subheader("Rent vs. Commute")
    figure = create_rent_vs_commute_figure(ranked_df, top_n_highlight=5)
    st.pyplot(figure, width="stretch")


if __name__ == "__main__":
    main()
