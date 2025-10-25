"""
FAO scraper functions for nutritional data (kcal, proteins, fats)
"""

import re
import requests
import pandas as pd
from bs4 import BeautifulSoup

USER_AGENT = "Project DALAS - academic scraping (contact: your.email@example.com)"

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


def extract_fao_data(html):
    """Extract data (food name, kcal, protein, fat) from FAO tables."""
    soup = BeautifulSoup(html, "lxml")
    tables = soup.find_all("table")
    data = []

    for table in tables:
        for row in table.find_all("tr"):
            cols = [c.get_text(strip=True) for c in row.find_all(["td", "th"])]
            if not cols or "ARTICLE" in cols[0].upper() or "Calories" in cols[0]:
                continue

            if len(cols) >= 8:
                data.append(cols[:4])
                data.append(cols[4:8])
            elif len(cols) == 4:
                data.append(cols)

    # Create DataFrame
    df = pd.DataFrame(data, columns=["food_name", "kcal", "protein", "fat"])

    # Clean data
    df["food_name"] = df["food_name"].astype(str).str.strip().str.lower()
    df["kcal"] = df["kcal"].apply(clean_numeric)
    df["protein"] = df["protein"].apply(clean_numeric)
    df["fat"] = df["fat"].apply(clean_numeric)

    # drop invalid rows
    df = df.dropna(subset=["food_name", "kcal"])
    df = df[df["food_name"].str.len() > 2]
    
    # Convert to per gram values
    df["kcal_per_g"] = df["kcal"] / 100
    df["protein_per_g"] = df["protein"] / 100
    df["fat_per_g"] = df["fat"] / 100
    
    # Keep only per gram values + food name
    df = df[["food_name", "kcal_per_g", "protein_per_g", "fat_per_g"]]


    return df
