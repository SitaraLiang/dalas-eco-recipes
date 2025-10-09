"""
Execution script for the scraper.
Imports and runs the functions defined in recipe_scraper.py.
"""
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.recipe_scraper import (
    get_recipe_links_query,
    get_recipe_links_category,
    collect_recipes
)


if __name__ == "__main__":
    # Collect vegetarian recipes via search query
    #vege_links = get_recipe_links_query("vege")
    #collect_recipes(vege_links, "recipes_vege.json")

    # Collect meat recipes via category
    meat_links = get_recipe_links_category("viande")
    collect_recipes(meat_links, "recipes_meat.json", limit=2000)


    print("\n✅ All scraping tasks completed successfully.")
