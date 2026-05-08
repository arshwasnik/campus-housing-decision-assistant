from __future__ import annotations

from pathlib import Path

import matplotlib
import pandas as pd


matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.style.use("ggplot")


def plot_rent_vs_distance(df: pd.DataFrame, output_path: Path | str) -> None:
    """Scatter plot showing rent per person against distance to campus."""
    figure, axis = plt.subplots(figsize=(10, 6))
    axis.scatter(
        df["distance_to_campus_miles"],
        df["rent_per_person"],
        s=90,
        alpha=0.8,
        color="#1f77b4",
        edgecolors="black",
    )
    axis.set_title("Rent Per Person vs. Distance to Campus")
    axis.set_xlabel("Distance to Campus (miles)")
    axis.set_ylabel("Rent Per Person (USD)")
    figure.tight_layout()
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, dpi=200)
    plt.close(figure)


def plot_top_apartments(df: pd.DataFrame, output_path: Path | str, top_n: int = 10) -> None:
    """Bar chart showing the highest-ranked apartments."""
    top_df = df.head(top_n).sort_values("overall_score")
    figure, axis = plt.subplots(figsize=(10, 6))
    axis.barh(top_df["property_name"], top_df["overall_score"], color="#2ca02c")
    axis.set_title(f"Top {top_n} Apartments by Overall Score")
    axis.set_xlabel("Overall Score")
    axis.set_ylabel("Apartment")
    figure.tight_layout()
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, dpi=200)
    plt.close(figure)


def plot_score_breakdown(df: pd.DataFrame, output_path: Path | str, top_n: int = 5) -> None:
    """Grouped bar chart comparing score components for the best listings."""
    score_columns = [
        "affordability_score",
        "commute_convenience_score",
        "space_value_score",
        "amenity_score",
        "safety_score",
        "hidden_cost_score",
    ]
    legend_labels = {
        "affordability_score": "Affordability",
        "commute_convenience_score": "Commute",
        "space_value_score": "Space/Value",
        "amenity_score": "Amenities",
        "safety_score": "Safety",
        "hidden_cost_score": "Low Hidden Cost Risk",
    }
    top_df = df.head(top_n).set_index("property_name")[score_columns].rename(columns=legend_labels)

    figure, axis = plt.subplots(figsize=(12, 7))
    top_df.plot(kind="bar", ax=axis)
    axis.set_title(f"Score Breakdown for Top {top_n} Listings")
    axis.set_xlabel("Apartment")
    axis.set_ylabel("Score")
    axis.legend(title="Score Type")
    figure.tight_layout()
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, dpi=200)
    plt.close(figure)
