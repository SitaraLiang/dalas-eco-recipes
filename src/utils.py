import re

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
    for ing in spec_ing:
        name = ing["ingredient_name"]
        quantity = ing["quantity"]
        avg_weight = spec_ing_weights.get(name, 1)
        total_weight = avg_weight * quantity
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
                ing["quantity"] = str(spec_lookup[ing_name]["total_weight"])
                ing["unit"] = "g"  # ensure consistent units

    return filtered_recipes


def scale_ecv(standalized_recipes):
    for recipe in standalized_recipes:
        for ing in recipe.get("ingredients", []):
            ecv = ing.get("ecv", 0)
            quantity = float(ing.get("quantity", 0))
            scaled_ecv = ecv / 1000 * quantity
            ing["ecv"] = scaled_ecv
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


def normalize_ingredients(filtered_recipes):
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
            quantity = ing.get("quantity", 0)

            try:
                quantity = float(quantity)
            except (ValueError, TypeError):
                continue  # skip invalid quantities

            # If no unit, assume grams
            if unit == "":
                ing["unit"] = "g"
                new_ingredients.append(ing)

            # Convert kg or L → g (assuming 1 L ≈ 1 kg for simplicity)
            elif unit in ("kg", "l"):
                ing["quantity"] = str(quantity * 1000)
                ing["unit"] = "g"
                new_ingredients.append(ing)

            # Convert centiliters → grams (approx. 1 cl = 10 g for water-like density)
            elif unit == "cl":
                ing["quantity"] = str(quantity * 10)
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
                    ing["quantity"] = str(comp_quantity)
                    ing["unit"] = comp_unit

                    # Ensure this ingredient stays in the final list
                    new_ingredients.append(ing)

        # Replace recipe's ingredient list
        recipe["ingredients"] = new_ingredients

    return filtered_recipes
