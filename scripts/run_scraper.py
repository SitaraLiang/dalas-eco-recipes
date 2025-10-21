"""
Execution script for the scraper.
Imports and runs the functions defined in recipe_scraper.py
and the FAO nutritional data scraper.
"""
import sys
import time
import json
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.recipe_scraper import (
    get_recipe_links_query,
    get_recipe_links_category,
    collect_recipes
)

from src.fao_scraper import fetch_page, extract_fao_data

BASE_URL = "https://www.fao.org/4/x9892f/x9892f0c.htm"
DELAY_SECONDS = 1.0
DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)
FAO_OUTPUT_JSON = DATA_DIR / "fao_clean.json"

def run_fao_scraper():
    print(f"Downloading {BASE_URL} ...")
    html = fetch_page(BASE_URL)
    time.sleep(DELAY_SECONDS)

    print("Extracting and cleaning data ...")
    df = extract_fao_data(html)

    if df.empty:
        print("No valid data extracted from FAO.")
        return

    print(f"Saving clean dataset to {FAO_OUTPUT_JSON} ...")
    with open(FAO_OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(df.to_dict(orient="records"), f, ensure_ascii=False, indent=2)

    print(f"FAO scraper done! {len(df)} rows saved in '{FAO_OUTPUT_JSON}'.")
    print("\nPreview:")
    print(df.head(5).to_string(index=False))


if __name__ == "__main__":
    
    print("------------------------------------------------------")
    print(" Recipe Scraper — Project DALAS")
    print("------------------------------------------------------")

    # Collect vegetarian recipes via search query
    vege_links = get_recipe_links_query("vege")
    collect_recipes(vege_links, "recipes_vege.json")

    # Collect meat recipes via category
    meat_links = get_recipe_links_category("viande")
    collect_recipes(meat_links, "recipes_non_vege.json", limit=2500)

    print("\nRecipe scraping tasks completed successfully.\n")

    print("------------------------------------------------------")
    print(" FAO Nutritional Data Scraper — Project DALAS")
    print("------------------------------------------------------")

    run_fao_scraper()

    print("\nAll scraping tasks completed successfully.")

