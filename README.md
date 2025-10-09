# dalas-eco-recipes
Comparative analysis of vegetarian and non-vegetarian recipes in France to evaluate their ecological impact using scraped recipe data and environmental impact datasets.



## Data Extraction

This project begins with a data collection phase that scrapes recipes from **[Marmiton.org](https://www.marmiton.org)** — one of the largest French cooking websites.  
The scraper gathers structured data such as recipe titles, ingredient lists, and ratings.


### 1. Install Dependencies

Before running the scraper, install all required packages:

```bash
pip install -r requirements.txt
```

### 2. Run a Test Scrape (Optional)

To verify that your environment is working correctly:

```bash
python test_scraper.py
```

This will scrape a few sample recipes (e.g., for “cake”) and save them to:

```bash
data/test_recipes.json
```

### 3. Extract Full Project Data

Once the test works, run the full scraper:

```bash
python run_scraper.py
```

This script will:

1. Import the core scraper functions from `recipe_scraper.py`.
2. Collect vegetarian recipes using Marmiton’s **search query** (`?aqt=vege`).
3. Collect meat recipes using Marmiton’s **category pages** (`/index/categorie/viande`).
4. Save both datasets as JSON files inside the `data/` directory.

After completion, you should see two new files:

```
data/recipes_vege.json
data/recipes_meat.json
```

Each JSON file contains structured recipe data such as:

```json
{
  "title": "Gratin de légumes au fromage",
  "url": "https://www.marmiton.org/recettes/recette_gratin-de-legumes-au-fromage_12345.aspx",
  "rating": "4.5",
  "ingredients": [
    {"ingredient_name": "courgette", "quantity": "2", "unit": "", "complement": null},
    {"ingredient_name": "fromage râpé", "quantity": "100", "unit": "g", "complement": null}
  ]
}
```

### 4. Next Steps

You can now use these JSON files for:

* **Data cleaning and preprocessing**
* **Feature extraction and Data analysis**
* **Model training (e.g., recipe recommendation, ingredient substitution, etc.)**

---

### Tip

If you plan to scrape new categories or queries, simply modify:

```python
get_recipe_links_query("your_query")
get_recipe_links_category("your_category")
```

in `run_scraper.py`.

```