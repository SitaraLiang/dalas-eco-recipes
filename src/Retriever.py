"""
Recipe Retrieval System

Goal: Retrieve similar recipes based on user quesries using FAISS + embeddings.
This module handles the retrieval component of the RAG pipeline.

Features:
- Text similarity via FAISS
- Vegetarian preference boost
- Healthy/low-calorie&fat boost
- Always-on eco+healthy scoring
- Hybrid ranking with FAISS, rating, vegetarian, eco/healthy
"""

import pandas as pd
import numpy as np
import faiss
import pickle
from pathlib import Path
from sentence_transformers import SentenceTransformer
import logging

logger = logging.getLogger(__name__)


class RecipeRetriever:
    def __init__(self, processed_data_dir: str = "data/processed"):
        self.processed_data_dir = Path(processed_data_dir)
    
        # Load embedding model
        logger.info("Loading sentence transformer model...")
        self.embedding_model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
        
        # Load FAISS index
        logger.info("Loading FAISS index...")
        index_path = self.processed_data_dir / "recipes_faiss.index"
        self.faiss_index = faiss.read_index(str(index_path))
        
        # Load recipe-level metadata
        logger.info("Loading recipes metadata...")
        metadata_path = self.processed_data_dir / "recipes_metadata.csv"
        self.recipe_metadata = pd.read_csv(metadata_path)
        
        # Load chunk metadata
        logger.info("Loading chunk metadata...")
        chunk_meta_path = self.processed_data_dir / "chunk_metadata.pkl"
        with open(chunk_meta_path, "rb") as f:
            self.chunk_metadata = pickle.load(f)
        
        logger.info("Retriever initialization completed successfully!")


    def encode_query(self, query: str) -> np.ndarray:
        emb = self.embedding_model.encode([query], show_progress_bar=False)[0]
        emb = emb.astype("float32")
        faiss.normalize_L2(emb.reshape(1, -1))
        return emb

    def search_similar_chunks(self, q_emb: np.ndarray, top_k: int = 50):
        q_emb = q_emb.reshape(1, -1)
        distances, indices = self.faiss_index.search(q_emb, top_k)
        return distances[0], indices[0]

    def get_recipe_details(self, recipe_ids: list[int]) -> pd.DataFrame:
        return self.recipe_metadata.iloc[recipe_ids]

    def format_retrieved_context(self, recipe_details):
        """
        Formats recipe details into a list of strings for each recipe, with detailed ingredients.

        Args:
            recipe_details (list of dict or pd.DataFrame): The recipe details returned by get_recipe_details.

        Returns:
            list of str: Formatted strings for each recipe.
        """
        formatted_context = []

        if hasattr(recipe_details, "to_dict"):
            recipe_details = recipe_details.to_dict(orient="records")

        for recipe in recipe_details:
            title = recipe.get("title", "No Title")
            ingredients = recipe.get("ingredients", [])
            rating = recipe.get("rating", "N/A")
            is_vege = "Yes" if recipe.get("is_vege", None) else "No"

            formatted_ingredients = []
            if isinstance(ingredients, list):
                for ing in ingredients:
                    name = ing.get("name", "Unknown")
                    quantity = ing.get("quantity", "")
                    unit = ing.get("unit", "")
                    if quantity and unit:
                        formatted_ingredients.append(f"{quantity} {unit} {name}")
                    elif quantity:
                        formatted_ingredients.append(f"{quantity} {name}")
                    else:
                        formatted_ingredients.append(name)
                ingredients_str = ", ".join(formatted_ingredients)
            else:
                ingredients_str = str(ingredients)

            formatted_string = (
                f"Recipe: {title}\n"
                f"Rating: {rating}\n"
                f"Vegetarian: {is_vege}\n"
                f"Ingredients: {ingredients_str}\n"
            )
            formatted_context.append(formatted_string)

        return formatted_context


    def retrieve_recipes(self,query: str,top_k: int = 10,rating_weight: float = 0.15,veg_boost_weight: float = 0.2,eco_healthy_weight: float = 0.5) -> pd.DataFrame:
        q_emb = self.encode_query(query)
        sim, chunk_ids = self.search_similar_chunks(q_emb, top_k=50)
        rows = []
        for score, cid in zip(sim, chunk_ids):
            meta = self.chunk_metadata[cid]
            rid = meta["recipe_id"]

            rows.append({
                "recipe_id": rid,
                "chunk_id": meta["chunk_id"],
                "faiss_score": float(score),
            })

        df = pd.DataFrame(rows)

        df = df.sort_values("faiss_score", ascending=False)
        df = df.groupby("recipe_id").first().reset_index()

        df["rating"] = df["recipe_id"].apply(lambda r: self.recipe_metadata.loc[r, "rating"])
        df["is_vegetarian"] = df["recipe_id"].apply(lambda r: self.recipe_metadata.loc[r, "is_vege"])
        df["avg_kcal"] = df["recipe_id"].apply(lambda r: self.recipe_metadata.loc[r, "avg_kcal"])
        df["avg_fat"] = df["recipe_id"].apply(lambda r: self.recipe_metadata.loc[r, "avg_fat"])
        df["avg_ecv"] = df["recipe_id"].apply(lambda r: self.recipe_metadata.loc[r, "avg_ecv"])

        df["rating_norm"] = df["rating"] / df["rating"].max()
        df["kcal_norm"] = 1 - (df["avg_kcal"] / df["avg_kcal"].max())  # lower kcal better
        df["fat_norm"] = 1 - (df["avg_fat"] / df["avg_fat"].max())     # lower fat better
        df["eco_norm"] = 1 - (df["avg_ecv"] / df["avg_ecv"].max())     # lower eco-impact better

        # Composite eco+healthy score
        df["eco_healthy_score"] = (0.4 * df["eco_norm"] + 0.3 * df["kcal_norm"] + 0.3 * df["fat_norm"])

        df["final_score"] = df["faiss_score"]
        df["final_score"] += rating_weight * df["rating_norm"]                # rating boost
        df["final_score"] += veg_boost_weight * df["is_vegetarian"]          # vegetarian boost
        df["final_score"] += eco_healthy_weight * df["eco_healthy_score"]    # healthy+eco

        df = df.sort_values("final_score", ascending=False)

        results_df = df.head(top_k)
        results = self.get_recipe_details(results_df["recipe_id"])
        results_formatted = self.format_retrieved_context(results)
        return results_formatted
