"""
FAO scraper for nutritional data (https://www.fao.org/4/x9892f/x9892f0c.htm)

Extracts kcal, proteins, and fats for each food item
and saves a single clean JSON file in /data/fao_clean.json
"""

import os
import re
import json
import time
import requests
import pandas as pd
from bs4 import BeautifulSoup
from pathlib import Path

# ---------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------
BASE_URL = "https://www.fao.org/4/x9892f/x9892f0c.htm"
USER_AGENT = "Project DALAS - academic scraping (contact: your.email@example.com)"
DELAY_SECONDS = 1.0

DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)
OUTPUT_JSON = DATA_DIR / "fao_clean.json"

# ---------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------
def fetch_page(url):
    """Download the HTML page."""
    headers = {"User-Agent": USER_AGENT}
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding
    return resp.text

def clean_numeric(value):
    """Convert string like '12,5' to float."""
    if not value:
        return None
    value = str(value).replace(",", ".").strip()
    match = re.search(r"([\d\.]+)", value)
    return float(match.group(1)) if match else None

# ---------------------------------------------------------------------
# Scraper
# ---------------------------------------------------------------------
def extract_fao_data(html):
    """Extract data (food name, kcal, protein, fat) from FAO tabs."""
    soup = BeautifulSoup(html, "lxml")
    tables = soup.find_all("table")
    data = []

    for table in tables:
        for row in table.find_all("tr"):
            cols = [c.get_text(strip=True) for c in row.find_all(["td", "th"])]
            # Ignore headers
            if not cols or "ARTICLE" in cols[0].upper() or "Calories" in cols[0]:
                continue

            # Two columns per row (left/right)
            if len(cols) >= 8:
                data.append(cols[:4])
                data.append(cols[4:8])
            elif len(cols) == 4:
                data.append(cols)

    # Create DataFrame
    df = pd.DataFrame(data, columns=["food_name", "kcal", "protein", "fat"])

    # Clean
    df["food_name"] = df["food_name"].astype(str).str.strip().str.upper()
    df["kcal"] = df["kcal"].apply(clean_numeric)
    df["protein"] = df["protein"].apply(clean_numeric)
    df["fat"] = df["fat"].apply(clean_numeric)

    # Delete empty rows or wrong
    df = df.dropna(subset=["food_name", "kcal"])
    df = df[df["food_name"].str.len() > 2]

    print(f"✅ {len(df)} aliments valides extraits.")
    return df

# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------
def main():
    print("------------------------------------------------------")
    print(" FAO Nutritional Data Scraper — Project DALAS")
    print("------------------------------------------------------")

    print(f"[*] Téléchargement de {BASE_URL} ...")
    html = fetch_page(BASE_URL)
    time.sleep(DELAY_SECONDS)

    print("[*] Extraction et nettoyage des données ...")
    df = extract_fao_data(html)

    if df.empty:
        print("[❌] Aucune donnée valide extraite.")
        return

    print(f"[*] Sauvegarde du dataset propre dans {OUTPUT_JSON} ...")

    # Save as JSON 
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(df.to_dict(orient="records"), f, ensure_ascii=False, indent=2)

    print(f"✅ Terminé ! {len(df)} lignes sauvegardées dans '{OUTPUT_JSON}'.")

    # Show first rows
    print("\nAperçu :")
    print(df.head(10).to_string(index=False))


if __name__ == "__main__":
    main()
