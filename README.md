# Campus Housing Decision Assistant

Campus Housing Decision Assistant is a small, data-focused project for comparing apartment listings near a college campus. The goal is to help students reason through tradeoffs with a transparent scoring system instead of a black-box recommendation model.

This prototype stays intentionally simple:

- load a CSV of apartment listings
- clean student-relevant housing fields
- engineer a handful of comparison features
- score listings using readable weighted rules
- parse natural language preferences into structured scoring inputs
- save ranked outputs and a few charts

There is no front end yet. The value of the project is the data pipeline and the explainable ranking logic. The preference parser is rule-based on purpose so the project can later evolve into an AI-assisted system where the model produces structured inputs instead of unsupported end-to-end recommendations.

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
|       |-- preference_parser.py
|       |-- visualization.py
|-- requirements.txt
|-- run_pipeline.py
|-- README.md
```

## Sample Dataset

The sample file at [data/raw/sample_apartments.csv](/C:/Users/Arsh/Desktop/campus-housing-decision-assistant/data/raw/sample_apartments.csv) includes 36 realistic listings near a UT Austin style campus area.

The dataset includes fields that matter to students:

- `rent`
- `bedrooms`
- `bathrooms`
- `square_feet`
- `distance_to_campus_miles`
- `commute_time_minutes`
- `parking_included`
- `laundry_included`
- `utilities_included`
- `furnished`
- `pet_friendly`
- `safety_rating`
- `walkability_score`
- `lease_length_months`
- `hidden_fees_estimate`

It also keeps:

- `property_name`
- `city`
- `state`
- `latitude`
- `longitude`
- `description`

The sample values still include realistic formatting like `$1,650/mo`, `2 bd`, `940 sqft`, `0.7 mi`, and `8 min`, so the cleaning step has something to do.

## Cleaning Logic

The pipeline standardizes the raw CSV into a predictable schema before ranking:

- numeric text such as `$2,050`, `3 bd`, `1,100 sqft`, and `12 min` is converted to numbers
- boolean-style text such as `Yes` and `No` is converted to `True` and `False`
- city and state formatting is normalized
- core missing numeric values are filled with medians
- ratings and bounded fields are clipped to sensible ranges
- if `distance_to_campus_miles` is missing, the pipeline can estimate distance from latitude and longitude
- if `commute_time_minutes` is missing, the pipeline estimates commute from distance

The core data prep lives in [src/campus_housing_decision_assistant/pipeline.py](/C:/Users/Arsh/Desktop/campus-housing-decision-assistant/src/campus_housing_decision_assistant/pipeline.py).

## Natural Language Preference Parsing

The parser lives in [src/campus_housing_decision_assistant/preference_parser.py](/C:/Users/Arsh/Desktop/campus-housing-decision-assistant/src/campus_housing_decision_assistant/preference_parser.py). It uses string matching and regular expressions to identify:

- maximum rent
- maximum commute time
- desired number of bedrooms
- desired amenities
- priority categories like price, commute, space, amenities, and safety

### Example Input

```text
I want something under $850 per month, within 15 minutes of campus, with parking and laundry. I care most about low rent and commute time.
```

### Example Parsed Output

```python
{
    "max_rent": 850,
    "max_commute_minutes": 15,
    "desired_bedrooms": None,
    "required_amenities": ["parking", "laundry"],
    "weights": {
        "affordability": 0.37,
        "commute": 0.30,
        "space": 0.12,
        "amenities": 0.14,
        "safety": 0.07,
    },
}
```

The exact weights are heuristic because they are derived from rule-based signals rather than an LLM.

### More Example Inputs

```text
I need a 2 bedroom place under $950 with laundry and furnished rooms. Space matters more than amenities.
```

```text
Find something close to campus. I care most about safety and commute, and I want parking.
```

```text
I want the cheapest option possible, ideally under $800, and I do not mind a smaller place.
```

The parser output is adapted into the same preference dictionary the ranking pipeline already uses. That separation is intentional:

1. natural language input comes in
2. the parser turns it into structured preferences
3. the ranking pipeline applies deterministic scoring rules

Later, a real LLM can replace or assist the parser without changing how recommendations are scored.

## Scoring System

Every listing gets component scores from `0` to `100`, then those components are combined into one `overall_score`.

### 1. Affordability

Affordability is based on `rent_per_person`:

- `rent_per_person = rent / total_people`
- listings at or below the student budget get `100`
- listings above the budget fall off linearly until they reach `0`

The default budget is controlled by `max_rent` in [run_pipeline.py](/C:/Users/Arsh/Desktop/campus-housing-decision-assistant/run_pipeline.py) through `DEFAULT_PREFERENCES`.

### 2. Commute Convenience

Commute convenience combines actual commute time and neighborhood walkability:

```text
commute_convenience_score =
    0.75 * commute_time_score
  + 0.25 * walkability_score
```

- `commute_time_score` rewards listings that stay within the preferred commute window
- `walkability_score` gives a boost to apartments where daily errands and campus access are easier without a car

### 3. Space / Value

This score combines room to live with what the student is paying for it:

```text
space_value_score =
    0.35 * space_score
  + 0.25 * value_score
  + 0.20 * bathroom_score
  + 0.10 * bedroom_fit_score
  + 0.10 * bedroom_preference_score
```

Where:

- `space_score` comes from `space_per_person`
- `value_score` rewards lower `rent_per_square_foot`
- `bathroom_score` rewards better bathroom-to-person ratios
- `bedroom_fit_score` checks whether the unit has enough bedrooms for the expected roommate setup
- `bedroom_preference_score` nudges listings toward the user's requested bedroom count without replacing the main space/value logic

### 4. Amenities

Amenities are scored from explicit listing fields:

- parking
- laundry
- utilities included
- furnished
- pet friendly

When the user names required amenities, the pipeline also calculates a `required_amenity_match_score`. It checks explicit amenity columns first, then falls back to the description when needed for amenities like `gym` or `internet`.

### 5. Safety

Safety is driven by the listing's `safety_rating`, with a small walkability contribution:

```text
safety_score =
    0.85 * safety_rating_score
  + 0.15 * walkability_score
```

### 6. Hidden Cost Risk

Hidden cost risk looks at both move-in fees and likely recurring extra costs.

First, the pipeline converts the fee estimate into a monthly burden:

```text
hidden_fees_monthly_per_person =
    (hidden_fees_estimate / lease_length_months) / total_people
```

Then it combines:

- `hidden_fee_burden_score`: higher when upfront fees are heavy after being spread across the lease
- `extra_cost_exposure_score`: higher when utilities, parking, or laundry are not included

```text
hidden_cost_risk_score =
    0.70 * hidden_fee_burden_score
  + 0.30 * extra_cost_exposure_score
```

The final ranking uses `hidden_cost_score = 100 - hidden_cost_risk_score`, so lower risk improves the recommendation.

## Overall Score Formula

The default priorities live in [src/campus_housing_decision_assistant/config.py](/C:/Users/Arsh/Desktop/campus-housing-decision-assistant/src/campus_housing_decision_assistant/config.py). They are normalized so the weights add up to `1.0`, then the pipeline computes:

```text
overall_score =
    affordability_weight * affordability_score
  + commute_weight * commute_convenience_score
  + space_value_weight * space_value_score
  + amenities_weight * amenity_score
  + safety_weight * safety_score
  + hidden_cost_weight * hidden_cost_score
```

That keeps the recommendation logic transparent and easy to tune.

## Default Preferences

The starting preferences are:

```python
DEFAULT_PREFERENCES = {
    "max_rent": 950,
    "max_commute_minutes": 15,
    "roommate_count": 1,
    "desired_bedrooms": None,
    "required_amenities": [],
    "priority_affordability": 0.30,
    "priority_commute": 0.20,
    "priority_space_value": 0.18,
    "priority_amenities": 0.14,
    "priority_safety": 0.12,
    "priority_hidden_cost": 0.06,
}
```

`roommate_count` means the number of roommates besides the student. A value of `1` means the apartment cost is split across `2` people.

## How To Run

1. Install dependencies:

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

Inside [run_pipeline.py](/C:/Users/Arsh/Desktop/campus-housing-decision-assistant/run_pipeline.py), you can optionally set `user_preference_text` to a plain-English request. When that string is present, the parser will:

- extract structured preferences
- merge them with defaults
- pass them into the ranking pipeline
- print both the parsed preferences and the final pipeline preferences

## Output Files

Running the script saves:

- [data/processed/cleaned_apartment_listings.csv](/C:/Users/Arsh/Desktop/campus-housing-decision-assistant/data/processed/cleaned_apartment_listings.csv)
- [data/processed/ranked_apartment_recommendations.csv](/C:/Users/Arsh/Desktop/campus-housing-decision-assistant/data/processed/ranked_apartment_recommendations.csv)
- figures in [outputs/figures](/C:/Users/Arsh/Desktop/campus-housing-decision-assistant/outputs/figures)

## Why This Design Is Useful

This version is a good stepping stone toward AI-assisted recommendations because it separates concerns cleanly:

- parsing is isolated in one module
- scoring stays deterministic and auditable
- the system can explain why a listing ranked well
- a future LLM can be added as a structured preference extraction layer instead of a black-box recommender
