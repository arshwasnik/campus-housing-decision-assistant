# Campus Housing Decision Assistant

Campus Housing Decision Assistant is an explainable student housing ranking system built in two phases:

1. Phase 1: data cleaning, feature engineering, and weighted apartment ranking
2. Phase 2: natural language preference parsing that turns a user sentence into structured scoring inputs

The project currently has no front end yet. It is intentionally focused on the data pipeline, scoring logic, and explainable preference parsing so it is easy to discuss in interviews and easy to extend later.

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

## Phase 1: Data Cleaning and Apartment Ranking

Phase 1 handles the ranking pipeline end to end:

- load apartment listings from [data/raw/sample_apartments.csv](data/raw/sample_apartments.csv)
- clean messy values such as rent strings, square footage text, and yes/no amenity fields
- engineer comparison features such as `rent_per_person`, `commute_convenience_score`, `space_value_score`, and `hidden_cost_score`
- rank apartments with weighted, transparent scoring rules
- save ranked CSV outputs and charts

The core ranking code lives in:

- [config.py](src/campus_housing_decision_assistant/config.py)
- [pipeline.py](src/campus_housing_decision_assistant/pipeline.py)
- [visualization.py](src/campus_housing_decision_assistant/visualization.py)

### What the ranking considers

The scoring system combines:

- affordability
- commute convenience
- space and value
- amenities
- safety
- hidden cost risk

This keeps the recommendation logic deterministic and explainable instead of acting like a black-box recommender.

## Phase 2: Natural Language Preference Parsing

Phase 2 adds a rule-based parser in [preference_parser.py](src/campus_housing_decision_assistant/preference_parser.py).

The parser is intentionally simple and explainable:

- it uses Python string matching
- it uses regular expressions
- it does not require an OpenAI API key
- it converts a plain-English sentence into structured inputs for the existing ranking pipeline

The parser can extract:

- maximum rent
- maximum commute time
- desired bedrooms
- required amenities
- priority weights for affordability, commute, space, amenities, safety, and hidden cost risk

### Example preference sentences

1. `I want something under $850 per month, within 15 minutes of campus, with parking and laundry. I care most about low rent, commute time, and avoiding hidden fees.`

This parser extracts:

- `max_rent = 850`
- `max_commute_minutes = 15`
- `required_amenities = ["parking", "laundry"]`
- higher weights for affordability, commute, and hidden cost risk

2. `I need a 2 bedroom place under $950 with laundry and furnished rooms. Space matters more than amenities.`

This parser extracts:

- `desired_bedrooms = 2`
- `max_rent = 950`
- `required_amenities = ["laundry", "furnished"]`
- a higher weight for space/value

3. `Find something close to campus. I care most about safety and commute, and I want parking.`

This parser extracts:

- a commute constraint when minutes are stated
- `required_amenities = ["parking"]`
- higher weights for safety and commute

### Why this design matters

Phase 2 is designed as a structured-input layer, not a direct recommendation engine:

1. the user writes a natural language preference sentence
2. the parser converts it into structured preferences
3. the existing ranking pipeline scores listings using deterministic logic

That makes the system easier to explain, easier to test, and easier to upgrade later if you want to add an LLM without changing the ranking core.

## Sample Dataset

The sample dataset in [data/raw/sample_apartments.csv](data/raw/sample_apartments.csv) includes realistic student-focused fields such as:

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

The raw values intentionally include realistic text formatting like `$1,650/mo`, `2 bd`, `940 sqft`, and `8 min` so the cleaning step is not trivial.

## How to Run

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the Phase 2 demo script:

```bash
python run_pipeline.py
```

The script:

- prints the original preference sentence
- parses it with the rule-based parser
- converts the parsed output into pipeline-ready preferences
- ranks the apartment listings
- prints the top 3 recommendations with key scores
- saves ranked outputs and charts

## Output Files

Running the script generates:

- `data/processed/cleaned_apartment_listings.csv`
- `data/processed/ranked_apartment_recommendations.csv`
- figures in `outputs/figures/`

## Why This Repo Looks Good in Interviews

This project now tells a clean, professional story:

- Phase 1 shows practical data cleaning and ranking logic
- Phase 2 shows how natural language can be translated into structured inputs
- the scoring remains explainable and auditable
- the architecture leaves room for a future AI layer without hiding the decision logic

That makes it a strong example of building an AI-adjacent product in a responsible, understandable way.
