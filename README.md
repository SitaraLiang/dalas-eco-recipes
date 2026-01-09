# dalas-eco-recipes

**Sustainable Recipe Analysis and Recommendation System**

This project compares **vegetarian and non-vegetarian recipes in France** to evaluate their **environmental impact, nutritional properties, and user ratings**, and proposes a **sustainable recipe recommendation system**.

Recipes are scraped from *Marmiton.org* and enriched with official **carbon footprint (CO₂)** and **nutritional** datasets.

---

## Project Highlights

* Recipe dataset scraped from Marmiton.org
* Environmental impact estimation (CO₂ emissions)
* Nutritional analysis (calories, protein, fat)
* Exploratory Data Analysis (EDA, correlations, PCA, outliers)
* Rating prediction (limited but informative)
* Hybrid eco-friendly recipe recommendation system

## Data Collection

### Install dependencies

```bash
pip install -r requirements.txt
```

### Test the scraper (optional)

```bash
python tests/test_scraper.py
```

### Run full scraping

```bash
python scripts/run_scraper.py
```

Generated files:

```
data/recipes_vege.json
data/recipes_meat.json
```


## Key Findings

* Vegetarian recipes have **significantly lower CO₂ emissions**, calories, and fat.
* User ratings show **weak correlation** with nutritional and environmental features.
* Sustainable recipes can still achieve **competitive ratings**.


## Recommendation System

A **hybrid retrieval + ranking approach** combining:

* Semantic similarity (text embeddings)
* Environmental impact
* Nutritional balance
* User ratings
* Vegetarian preference

The system promotes **eco-friendly and healthy recipes** without sacrificing user appeal.


## Limitations

* Single recipe source (French cuisine bias)
* Approximate nutritional and environmental estimates
* No real user interaction data
* Limited rating variability


## Future Work

* Multi-source datasets
* User feedback integration
* Interactive recommendation interface
