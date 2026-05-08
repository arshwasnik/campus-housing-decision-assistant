# Campus Housing Decision Assistant

Campus Housing Decision Assistant is a focused AI-assisted decision system for student housing.

The core idea is simple:

1. a user writes housing preferences in plain English
2. the system converts that text into structured ranking inputs
3. an explainable weighted model scores apartment listings
4. the system returns top recommendations with plain-English explanations of strengths and tradeoffs

The project is intentionally small and deterministic. It does not use React, a database, or an LLM API in the current version.

## Final Project Phases

### Phase 1: Explainable Housing Ranking

Phase 1 handles the ranking pipeline end to end:

- load apartment listings from [data/raw/sample_apartments.csv](data/raw/sample_apartments.csv)
- clean messy housing fields such as rent strings, square footage text, and yes/no amenity fields
- engineer student-centered features such as `rent_per_person`, `space_per_person`, `commute_convenience_score`, and `hidden_cost_score`
- rank listings with a transparent weighted scoring model
- save cleaned outputs, ranked outputs, and visualizations

The ranking model considers:

- affordability
- commute convenience
- space and value
- amenities
- safety
- hidden cost risk

### Phase 2: Natural Language Preference Parsing

Phase 2 adds a rule-based parser in [preference_parser.py](src/campus_housing_decision_assistant/preference_parser.py).

The parser is intentionally explainable:

- it uses Python string matching
- it uses regular expressions
- it does not call the OpenAI API
- it converts a user sentence into structured inputs for the existing scoring pipeline

The parser can extract:

- maximum rent
- maximum commute time
- desired bedrooms
- required amenities
- priority weights for affordability, commute, space/value, amenities, safety, and hidden cost risk

This means the recommendation flow stays consistent:

1. parse the user sentence
2. build pipeline-ready preferences
3. rank apartments with the existing deterministic scoring model

### Phase 3: Streamlit Demo with Recommendation Explanations

Phase 3 adds two lightweight product-facing pieces:

- recommendation explanations generated from score columns, apartment fields, and parsed preferences
- a simple [app.py](app.py) Streamlit demo

Each top recommendation now includes a `recommendation_explanation` that describes:

- why the apartment ranked highly
- which user preferences it matched
- strongest factors such as affordability, commute, safety, amenities, or space
- one tradeoff when relevant, such as higher rent, longer commute, smaller space, missing amenities, or hidden fees

These explanations are rule-based and deterministic. They do not use an LLM in the current version.

## Project Structure

```text
campus-housing-decision-assistant/
|-- app.py
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
|       |-- recommendation_explainer.py
|       |-- visualization.py
|-- requirements.txt
|-- run_pipeline.py
|-- README.md
```

## How to Run

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the command-line pipeline demo:

```bash
python run_pipeline.py
```

This script:

- loads and cleans the apartment data
- parses an example natural language preference sentence
- converts parsed preferences into ranking inputs
- ranks the listings
- saves cleaned data, ranked data, and figures
- prints top recommendations and their explanations

Run the Streamlit demo:

```bash
streamlit run app.py
```

The Streamlit app:

- accepts natural language housing preferences
- uses the existing rule-based parser
- runs the same explainable ranking pipeline
- shows top apartment recommendations
- shows plain-English recommendation explanations
- displays a ranked results table
- includes a simple rent-versus-commute visualization

## Output Files

Running the pipeline generates:

- `data/processed/cleaned_apartment_listings.csv`
- `data/processed/ranked_apartment_recommendations.csv`
- figures in `outputs/figures/`

The ranked recommendations CSV now includes a `recommendation_explanation` column.

## Future Extension

A future version could replace or supplement the current rule-based parser with an LLM-based JSON preference extractor.

That would make preference extraction more flexible while still preserving the existing ranking pipeline as the explainable recommendation core.
