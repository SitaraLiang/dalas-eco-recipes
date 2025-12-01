import re


def handle_empty_quantity(recipes, ing_empty_quantity):
    from statistics import mean  # built-in for averaging

    ing_with_quantity = {}

    # Step 1: collect (quantity, unit) pairs
    for ing in ing_empty_quantity:
        for recipe in recipes:
            for ingredient in recipe.get("ingredients", []):
                if ing == ingredient.get("ingredient_name"):
                    quantity = ingredient.get("quantity")
                    unit = ingredient.get("unit")

                    # Skip if quantity/unit missing or empty
                    if quantity not in [None, ""] and unit not in [None, ""]:
                        try:
                            quantity = float(quantity)
                        except (ValueError, TypeError):
                            continue  # skip non-numeric
                        if ing not in ing_with_quantity:
                            ing_with_quantity[ing] = []
                        ing_with_quantity[ing].append((quantity, unit))

    # Step 2: summarize — prefer "g" over "kg"
    summarized = {}

    for ing, values in ing_with_quantity.items():
        # Separate quantities by unit
        g_values = [q for q, u in values if u == "g"]
        kg_values = [q for q, u in values if u == "kg"]

        if g_values:
            summarized[ing] = (mean(g_values), "g")
        elif kg_values:
            summarized[ing] = (mean(kg_values), "kg")
        else:
            # If neither, you can choose to skip or pick the first
            summarized[ing] = values[0] if values else (0.0, None)

    return summarized

def update_recipes_with_quantities(recipes, ing_with_quantity):
    """
    Update all ingredients in recipes that have quantity == 0.0 and unit == ""
    using the summarized ing_with_quantity dictionary.

    Args:
        recipes (list): list of recipe dicts
        ing_with_quantity (dict): {ingredient_name: (mean_quantity, unit)}

    Returns:
        list: updated recipes (same object, modified in place)
    """
    for recipe in recipes:
        for ingredient in recipe.get("ingredients", []):
            name = ingredient.get("ingredient_name")
            quantity = ingredient.get("quantity")
            unit = ingredient.get("unit")

            # Check for missing/empty quantity
            if (quantity in [0, 0.0, None, ""]):
                if name in ing_with_quantity:
                    mean_qty, mean_unit = ing_with_quantity[name]
                    ingredient["quantity"] = mean_qty
                    ingredient["unit"] = mean_unit
    return recipes



def get_empty_quantity(recipes):
    ing = set()
    for recipe in recipes:
        for ingredient in recipe.get("ingredients", []):
            quantity = ingredient.get("quantity")
            if quantity == 0:
                ing.add(ingredient["ingredient_name"])

    return list(ing)

def convert_recipe_numbers(recipes: list) -> list:
    """
    Convert quantity in ingredients and rating of each recipe to float.
    
    Args:
        recipes (list): List of recipe dictionaries.
        
    Returns:
        list: Updated list of recipes with float quantities and ratings.
    """
    for recipe in recipes:
        rating = recipe.get("rating")
        if rating is None:  # Handle NoneType values
            recipe["rating"] = None
        else:
            try:
                recipe["rating"] = float(rating)
            except (ValueError, TypeError):
                recipe["rating"] = 0.0

        for ingredient in recipe.get("ingredients", []):
            try:
                quantity = float(ingredient.get("quantity", 0))
                if quantity < 0:
                    quantity *= -1
                ingredient["quantity"] = quantity
            except ValueError:
                ingredient["quantity"] = 0.0

    return recipes

def get_unique_ingredients(recipes: list) -> list:
    """
    Returns a sorted list of all unique ingredient names 
    found across all recipes.
    """
    ingredients_set = set()

    for recipe in recipes:
        for ing in recipe.get("ingredients", []):
            name = ing.get("ingredient_name", "").strip().lower()
            if name:
                ingredients_set.add(name)

    return sorted(ingredients_set)

# Filter ingredients and remove recipes with empty ingredient lists
def filter_recipes_based_on_ecv(recipes: list, ecv_dict: dict) -> list:
    """
    Adds 'ecv' to ingredients and filters out those without ECV data.
    Returns a cleaned list of recipes.
    """

    def get_ecv(ingredient_name: str) -> str:
        ingredient_name_lower = ingredient_name.strip().lower()
        for slug, ecv in ecv_dict.items():
            if slug in ingredient_name_lower:
                return ecv
        return ""

    enriched_recipes = []
    for recipe in recipes:
        ingredients = recipe.get("ingredients", [])
        for ing in ingredients:
            ing["ecv"] = get_ecv(ing.get("ingredient_name", ""))
        # Keep only ingredients with ECV
        recipe["ingredients"] = [ing for ing in ingredients if ing["ecv"]]
        if recipe["ingredients"]:
            enriched_recipes.append(recipe)

    return enriched_recipes


def filter_recipes(recipes: list, ecv_data: dict, is_vege: bool) -> list:
    # Collect all slugs under 'viandes' or 'poissons' categories
    meat_fish_slugs = set()
    for category in ecv_data.get("data", []):
        category_slug = category.get("slug", "").lower()
        if category_slug in ("viandes", "poissons"):
            for item in category.get("items", []):
                slug = item.get("slug", "").lower()
                meat_fish_slugs.add(slug)

    filtered_recipes = []
    for recipe in recipes:
        ingredients = recipe.get("ingredients", [])
        if ingredients == []:
            continue
        # Check if any ingredient name contains a meat/fish slug
        has_meat_or_fish = any(
            any(slug in ing.get("ingredient_name", "").lower() for slug in meat_fish_slugs)
            for ing in ingredients
        )
        if not is_vege:
            if has_meat_or_fish:
                filtered_recipes.append(recipe)
        elif is_vege:
            if not has_meat_or_fish:
                filtered_recipes.append(recipe)

    return filtered_recipes


def add_weights(spec_ing, spec_ing_weights):
    """
    Add total_weight to each ingredient in spec_ing by multiplying its quantity 
    by the corresponding average weight from spec_ing_weights.

    Handles small naming variations (plurals, case, partial matches).

    Args:
        spec_ing (list): list of ingredient dicts, each with 'ingredient_name' and 'quantity'
        spec_ing_weights (dict): {ingredient_name: avg_weight}

    Returns:
        list: updated spec_ing with 'total_weight' added
    """
    for ing in spec_ing:
        name = ing.get("ingredient_name", "").strip().lower()
        quantity = ing.get("quantity")
        avg_weight = 1

        # Try direct match first
        for key in spec_ing_weights:
            key_norm = key.strip().lower()
            # Handle plural forms and partial matches
            if key_norm == name:
                avg_weight = spec_ing_weights[key]
                break
            elif (key_norm.rstrip('s') == name.rstrip('s')  # singular/plural tolerance
                or key_norm in name
                or name in key_norm
            ):
                avg_weight = spec_ing_weights[key]

        # Compute total weight
        total_weight = quantity * avg_weight if quantity != 0 else avg_weight

        ing["total_weight"] = total_weight

    return spec_ing



def standardize_recipes(filtered_recipes, spec_ing):
    """
    For each ingredient in spec_ing, set its 'total_weight' as the 'quantity'
    in all corresponding recipes inside filtered_recipes.

    Args:
        filtered_recipes (list): list of recipe dicts with 'title' and 'ingredients'.
        spec_ing (list): list of dicts like
            {'ingredient_name': str, 'quantity': float, 'recipes': [str], 'total_weight': float}

    Returns:
        list: updated filtered_recipes (modified in place and also returned).
    """
    # ingredient_name -> (recipes, total_weight)
    spec_lookup = {
        i["ingredient_name"].lower(): {
            "recipes": [r.lower() for r in i.get("recipes", [])],
            "total_weight": i.get("total_weight", 0),
        }
        for i in spec_ing
    }

    for recipe in filtered_recipes:
        title = recipe.get("title", "").strip().lower()
        for ing in recipe.get("ingredients", []):
            ing_name = ing.get("ingredient_name", "").strip().lower()
            if not ing_name:
                continue

            # If ingredient matches and recipe title is in its list
            if ing_name in spec_lookup and title in spec_lookup[ing_name]["recipes"]:
                ing["quantity"] = spec_lookup[ing_name]["total_weight"]
                ing["unit"] = "g"  # ensure consistent units

    return filtered_recipes


def scale_ecv(standalized_recipes):
    for recipe in standalized_recipes:
        recipe["total_ecv"] = 0
        for ing in recipe.get("ingredients", []):
            ecv = ing.get("ecv", 0)
            quantity = float(ing.get("quantity", 0))
            scaled_ecv = ecv / 1000 * quantity
            ing["ecv"] = scaled_ecv
            recipe["total_ecv"] += ing["ecv"]
    return standalized_recipes


def extract_spec_ingredients(filtered_recipes, max_quantity=16):
    """
    Extracts unique ingredients from filtered_recipes that have a quantity <= max_quantity.
    Returns a list of unique special ingredient names with their corresponding quantities
    and the recipe titles they appear in.
    """
    ingredients = {}  # key = ingredient_name, value = {"quantity": float, "recipes": [titles]}

    for recipe in filtered_recipes:
        title = recipe.get("title", "Unknown recipe")

        for ing in recipe.get("ingredients", []):
            try:
                quantity = float(ing.get("quantity", 0))
            except (ValueError, TypeError):
                continue  # skip invalid quantities

            if quantity <= max_quantity:
                ing_name_lower = ing.get("ingredient_name", "").strip().lower()
                if not ing_name_lower:
                    continue

                if ing_name_lower not in ingredients:
                    ingredients[ing_name_lower] = {"quantity": quantity, "recipes": [title]}
                else:
                    # Keep the smallest quantity (if multiple found)
                    ingredients[ing_name_lower]["quantity"] = min(
                        ingredients[ing_name_lower]["quantity"], quantity
                    )

                    # Add recipe title if not already listed
                    if title not in ingredients[ing_name_lower]["recipes"]:
                        ingredients[ing_name_lower]["recipes"].append(title)

    result = [
        {
            "ingredient_name": name,
            "quantity": data["quantity"],
            "recipes": data["recipes"],
        }
        for name, data in ingredients.items()
    ]

    return result


def normalize_unit_quantity(filtered_recipes):
    """
    Normalize ingredient quantities and units in recipes.

    - Converts units to grams ('g').
    - Handles complements like "de 1 à 1,2 kg".
    - Drops ingredients with unsupported or invalid units.
    - Updates the 'ingredients' list in each recipe.

    Args:
        filtered_recipes (list): List of recipes, each with an 'ingredients' list.

    Returns:
        list: The updated list of recipes with normalized ingredients.
    """
    for recipe in filtered_recipes:
        new_ingredients = []
        for ing in recipe.get("ingredients", []):
            unit = ing.get("unit", "").strip().lower()
            quantity = float(ing.get("quantity", 0))

            # If no unit, assume grams
            if unit == "":
                ing["unit"] = "g"
                new_ingredients.append(ing)

            # Convert kg or L → g (assuming 1 L ≈ 1 kg for simplicity)
            elif unit in ("kg", "l"):
                ing["quantity"] = quantity * 1000
                ing["unit"] = "g"
                new_ingredients.append(ing)

            # Convert centiliters → grams (approx. 1 cl = 10 g for water-like density)
            elif unit == "cl":
                ing["quantity"] = quantity * 10
                ing["unit"] = "g"
                new_ingredients.append(ing)

            # Do nothing
            elif unit == "g":
                new_ingredients.append(ing)
            
            else:
                # Parse "complement" text for alternative quantities
                complement = ing.get("complement", "")
                match = re.search(r"(\d+[.,]?\d*)\s*(?:à\s*(\d+[.,]?\d*))?\s*(kg|g|l|cl)?", complement.lower())
                if match:
                    # Use upper bound if available
                    comp_quantity = float(match.group(2).replace(",", ".")) if match.group(2) else float(match.group(1).replace(",", "."))
                    comp_unit = match.group(3) or "g"

                    # Convert complement quantity units
                    if comp_unit in ("kg", "l"):
                        comp_quantity *= 1000
                        comp_unit = "g"
                    elif comp_unit == "cl":
                        comp_quantity *= 10
                        comp_unit = "g"

                    # Update ingredient with parsed complement info
                    ing["quantity"] = comp_quantity
                    ing["unit"] = comp_unit

                    # Ensure this ingredient stays in the final list
                    new_ingredients.append(ing)

        # Replace recipe's ingredient list
        recipe["ingredients"] = new_ingredients

    return filtered_recipes


import re
import unicodedata

# Step 1: remove accents
def strip_accents(text):
    return ''.join(
        c for c in unicodedata.normalize('NFD', text)
        if unicodedata.category(c) != 'Mn'
    )

# Step 2: basic cleanup and singularization
def linguistic_normalize(text, nlp):
    text = text.lower().strip()
    #text = strip_accents(text)
    text = re.sub(r"\bdes\b", "de", text)
    text = re.sub(r"\bdu\b", "de", text)
    text = re.sub(r"\bd'\b", "de ", text)
    text = re.sub(r"\s+", " ", text)
    doc = nlp(text)
    return ' '.join([t.lemma_ for t in doc])

def collapse_to_family(text, reverse_map):
    for pattern, canonical in reverse_map.items():
        if pattern in text:
            return canonical
    return text  # fallback if no match

# Full pipeline
def normalize_ingredient(ing, nlp, reverse_map):
    ing = linguistic_normalize(ing, nlp)
    ing = collapse_to_family(ing, reverse_map)
    return ing

def ing_to_fao_match(fao_table, normalized_ing):
    table = {}

    for ing in normalized_ing:
        table[ing] = {
            "kcal_per_g": [],
            "protein_per_g": [],
            "fat_per_g": []
        }
        for food in fao_table:
            food_name = food["food_name"]
            if ing in food_name:
                table[ing]["kcal_per_g"].append(food["kcal_per_g"])
                table[ing]["protein_per_g"].append(food["protein_per_g"])
                table[ing]["fat_per_g"].append(food["fat_per_g"])
    return table


def get_empty_fao(ing_to_fao):
    ing_with_empty_fao = []

    for ing, nutrients in ing_to_fao.items():
        # Check if all lists in the nested dictionary are empty
        if all(len(values) == 0 for values in nutrients.values()):
            ing_with_empty_fao.append(ing)
    return ing_with_empty_fao

def get_fao_info(ing_to_fao, ing_nutrition):
    for ing, nutrients in ing_to_fao.items():
        if all(len(values) == 0 for values in nutrients.values()):
            fao_info = ing_nutrition[ing]
            ing_to_fao[ing]["kcal_per_g"].append(fao_info["kcal_per_g"])
            ing_to_fao[ing]["protein_per_g"].append(fao_info["protein_per_g"])
            ing_to_fao[ing]["fat_per_g"].append(fao_info["fat_per_g"])
    return ing_to_fao

def normalize_fao_info(ing_to_fao):
    for ing, nutrients in ing_to_fao.items():
        for key, values in nutrients.items():
            if values:
                mean_value = sum(values) / len(values)
                nutrients[key] = mean_value
            else:
                nutrients[key] = 0
    return ing_to_fao


def calculate_recipe_nutrients(recipes: list, ing_to_fao: dict) -> list:
    """
    Calculate total calories, protein, and fat for each recipe in a list.

    Args:
        recipes (list): A list of recipe dictionaries, each with an 'ingredients' key.
        ing_to_fao (dict): A mapping of ingredient names to nutrient info 
                           (keys: kcal_per_g, protein_per_g, fat_per_g).

    Returns:
        list: The updated list of recipes with nutrient information added.
    """
    for recipe in recipes:
        ingredients = recipe.get("ingredients", [])
        recipe["total_kcal"] = 0
        recipe["total_protein"] = 0
        recipe["total_fat"] = 0

        for i in ingredients:
            ing_name = i.get("ingredient_name", "")
            qty = float(i.get("quantity", 0))

            for ing, nutrients in ing_to_fao.items():
                if ing.lower() in ing_name.lower():
                    kcal_per_g = nutrients.get("kcal_per_g", 0)
                    protein_per_g = nutrients.get("protein_per_g", 0)
                    fat_per_g = nutrients.get("fat_per_g", 0)

                    kcal_per_g = kcal_per_g * qty
                    protein_per_g = protein_per_g * qty
                    fat_per_g = fat_per_g * qty

                    recipe["total_kcal"] += kcal_per_g
                    recipe["total_protein"] += protein_per_g
                    recipe["total_fat"] += fat_per_g

    return recipes
