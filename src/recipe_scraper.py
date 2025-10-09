"""
Core scraper module for Marmiton (https://www.marmiton.org).

Contains functions to scrape recipes by query or category.
Used by run_scraper.py
"""

import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import time
import json
import pandas as pd
from tqdm import tqdm
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# ---------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------
BASE_URL = "https://www.marmiton.org"
SEARCH_URL = f"{BASE_URL}/recettes/recherche.aspx?aqt="
CATEGORY_URL = f"{BASE_URL}/recettes/index/categorie/"
HEADERS = {"User-Agent": "Mozilla/5.0"}

DATA_DIR = "data"


# Ensure the data directory exists
os.makedirs(DATA_DIR, exist_ok=True)

# ---------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------
def get_recipe_links_query(query):
    """Collect recipe links from the search results for a given query."""
    print(f"\nCollecting links for search query: '{query}'")
    url = f"{SEARCH_URL}{query}"
    r = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(r.text, "lxml")

    # Determine number of pages
    max_page = max(
        (int(a["href"].split("page=")[-1])
         for a in soup.select(".pagination__page-link") if "page=" in a["href"]),
        default=1
    )
    print(f"Number of pages found: {max_page}")

    links = []
    with tqdm(
        total=max_page,
        desc=f"Fetching {query} pages",
        unit="page",
        dynamic_ncols=True,
        leave=True,
        mininterval=1,
        file=sys.stdout) as pbar:
        for page in range(1, max_page + 1):
            page_url = f"{SEARCH_URL}{query}" + (f"&page={page}" if page > 1 else "")
            r = requests.get(page_url, headers=HEADERS)
            soup = BeautifulSoup(r.text, "lxml")

            for a in soup.select(".card-content__title"):
                href = a.get("href")
                if href:
                    links.append(urljoin(BASE_URL, href))
            time.sleep(1)
            pbar.update(1)

    print(f"✅ Total links collected for '{query}': {len(links)}")
    return links


def get_recipe_links_category(category):
    """Collect recipe links from a given category page."""
    print(f"\nCollecting links for category: '{category}'")
    url = f"{CATEGORY_URL}{category}"
    r = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(r.text, "lxml")

    max_page = max(
        (int(a.get_text()) for a in soup.select(".pagination__page-link")),
        default=1
    )
    print(f"Number of pages found: {max_page}")

    links = []
    with tqdm(
        total=max_page,
        desc=f"Fetching {category} pages",
        unit="page",
        dynamic_ncols=True,
        leave=True,
        mininterval=1,
        file=sys.stdout) as pbar:
        for page in range(1, max_page + 1):
            page_url = url + (f"/{page}" if page > 1 else "")
            r = requests.get(page_url, headers=HEADERS)
            soup = BeautifulSoup(r.text, "lxml")

            for a in soup.select("a.card-content__title"):
                href = a.get("href")
                if href:
                    links.append(urljoin(BASE_URL, href))
            time.sleep(1)
            pbar.update(1)

    print(f"✅ Total links collected for '{category}': {len(links)}")
    return links


def parse_recipe(url):
    """Extract details from a single recipe page."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(r.text, "lxml")

        title = soup.find("h1").text.strip() if soup.find("h1") else "N/A"

        ingredients = []
        for ing in soup.select(".card-ingredient-content"):
            name = ing.select_one(".ingredient-name")
            quantity = ing.select_one(".count")
            unit = ing.select_one(".unit")
            complement = ing.select_one(".ingredient-complement")

            ingredients.append({
                "ingredient_name": name.get_text(strip=True) if name else None,
                "quantity": quantity.get_text(strip=True) if quantity else None,
                "unit": unit.get_text(strip=True) if unit else None,
                "complement": complement.get_text(strip=True) if complement else None
            })

        rate_tag = soup.select_one(".recipe-header__rating-text")
        rate = rate_tag.get_text(strip=True).split("/")[0] if rate_tag else None

        return {
            "title": title,
            "url": url,
            "rating": rate,
            "ingredients": ingredients
        }
    except Exception as e:
        print(f"⚠️ Error parsing {url}: {e}")
        return None


def collect_recipes(links, output_filename, limit=None):
    """Parse all recipe links and save results to a JSON file in /data."""
    count = len(links) if not limit else min(limit, len(links))
    print(f"\nParsing {count} recipes...")

    recipes = []
    with tqdm(
        total=count,
        desc=f"Parsing recipes",
        unit="recipe",
        dynamic_ncols=True,
        leave=True,
        mininterval=1,
        file=sys.stdout) as pbar:
        for i, link in enumerate(links[:limit] if limit else links):
            data = parse_recipe(link)
            if data:
                recipes.append(data)
            pbar.update(1)
            time.sleep(1)

    df = pd.DataFrame(recipes)
    output_path = os.path.join(DATA_DIR, output_filename)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(df.to_dict(orient="records"), f, ensure_ascii=False, indent=2)

    print(f"\n✅ Saved {len(recipes)} recipes to '{output_path}'")
    return df