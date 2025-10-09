"""
A minimal test script to validate that the scraper works correctly
Saves results to data/test_recipes.json.
"""
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.recipe_scraper import (
    get_recipe_links_query,
    collect_recipes
)

if __name__ == "__main__":
    print("Starting Marmiton scraper test...")

    # Test a small query
    test_query = "cake"

    # Collect links (only from the first page)
    print(f"\nTesting link collection for query: '{test_query}'")
    links = get_recipe_links_query(test_query)

    if not links:
        print("❌ No links found — check your internet connection or Marmiton site structure.")
    else:
        print(f"✅ Found {len(links)} links (showing first 3):")
        for link in links[:3]:
            print("   ", link)

        # Parse just a few recipes 
        print("\nTesting recipe parsing (3 recipes)...")
        collect_recipes(links, "test_recipes.json", limit=3)

        print("\n✅ Test complete! Check 'data/test_recipes.json' for results.")
