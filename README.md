# Campus Housing Decision Assistant

Campus Housing Decision Assistant is a data science focused project for comparing apartment listings near a college campus. The goal is to help students make better housing decisions using a transparent scoring algorithm, not a black-box recommendation system.

This Phase 1 version focuses on the core analytics pipeline:

- Load apartment listings from a CSV file
- Clean messy housing data with Pandas
- Engineer comparison features that matter to students
- Rank listings using a weighted and explainable scoring method
- Save results and visualizations for easy review

Future phases can add AI for natural language preference parsing, description extraction, and plain-English recommendation summaries, but the project already works without AI.

## Project Structure

```text
campus-housing-decision-assistant/
|-- data/
|   |-- raw/
|   |   |-- sample_apartments.csv
|   |-- processed/
|-- outputs/
|   |-- figures/
|-- src/
|   |-- campus_housing_decision_assistant/
|       |-- __init__.py
|       |-- config.py
|       |-- pipeline.py
|       |-- visualization.py
|-- requirements.txt
|-- run_pipeline.py
|-- README.md
```

## Dataset

The project starts with a small sample CSV in [data/raw/sample_apartments.csv](/C:/Users/Arsh/Desktop/house-hunting-project/data/raw/sample_apartments.csv). It includes common apartment fields:

- `rent`
- `bedrooms`
- `bathrooms`
- `square_feet`
- `city`
- `state`
- `latitude`
- `longitude`
- `description`

The sample data intentionally includes messy formats like `$1,650/mo`, `2 bd`, and `940 sqft` so the cleaning step is realistic.

You can swap in a real dataset later by replacing the CSV and keeping the same column names.

## How The Scoring Works

The ranking system is fully transparent. Every listing gets component scores from `0` to `100`, then the final score is calculated with user-defined weights.

### Engineered Features

- `rent_per_person`: total rent divided by the number of people living there
- `rent_per_bedroom`: total rent divided by bedrooms
- `rent_per_square_foot`: total rent divided by square feet
- `bathroom_ratio`: bathrooms per person
- `space_per_person`: square feet per person
- `affordability_score`: higher when a listing stays within the student budget
- `commute_score`: higher when the estimated commute stays within the preferred limit
- `comfort_score`: combines space per person, bathroom ratio, and bedroom fit
- `amenity_score`: counts useful student-friendly amenities found in the description
- `hidden_cost_risk_score`: flags likely extra expenses mentioned in the description
- `overall_score`: weighted score minus a small hidden-cost penalty

### Preferences Dictionary

Edit the preferences dictionary in [run_pipeline.py](/C:/Users/Arsh/Desktop/house-hunting-project/run_pipeline.py):

```python
student_preferences = {
    "max_rent": 900,
    "max_commute_minutes": 15,
    "roommate_count": 1,
    "priority_budget": 0.35,
    "priority_commute": 0.25,
    "priority_space": 0.15,
    "priority_bathrooms": 0.15,
    "priority_amenities": 0.10,
}
```

`roommate_count` means the number of roommates besides the student. For example, `1` means the student plans to live with one roommate, so the apartment cost is split across `2` people.

### Overall Score Formula

The project normalizes the user priorities so they add up to `1.0`, then computes:

```text
overall_score =
    budget_weight * affordability_score
  + commute_weight * commute_score
  + space_weight * space_score
  + bathroom_weight * bathroom_score
  + amenity_weight * amenity_score
  - hidden_cost_penalty_weight * hidden_cost_risk_score
```

This makes the recommendation logic easy to explain in an interview.

## Visualizations

The pipeline creates three figures in [outputs/figures](/C:/Users/Arsh/Desktop/house-hunting-project/outputs/figures):

- Rent per person vs. distance to campus
- Top apartments by overall score
- Score breakdown for the top 5 listings

## How To Run

1. Install the dependencies:

```bash
pip install -r requirements.txt
```

2. Run the pipeline:

```bash
python run_pipeline.py
```

If `python` is not available on your machine, try:

```bash
py run_pipeline.py
```

## Output Files

Running the script saves:

- [data/processed/cleaned_apartment_listings.csv](/C:/Users/Arsh/Desktop/house-hunting-project/data/processed/cleaned_apartment_listings.csv)
- [data/processed/ranked_apartment_recommendations.csv](/C:/Users/Arsh/Desktop/house-hunting-project/data/processed/ranked_apartment_recommendations.csv)
- Figures in [outputs/figures](/C:/Users/Arsh/Desktop/house-hunting-project/outputs/figures)

## Why This Is Good For Interviews

This project is strong interview material because it shows:

- Data cleaning with Pandas
- Feature engineering tied to a real user problem
- Transparent scoring instead of black-box modeling
- Clear assumptions and tradeoff analysis
- Room to extend the project with AI later

## Phase 2 Ideas

After Phase 1 is stable, the next steps could be:

- Natural language preference parser
- AI-based description feature extraction
- Tradeoff explanation generator

Those features should be layered on top of the existing pipeline rather than replacing it.
