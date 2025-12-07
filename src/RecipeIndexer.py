#!/usr/bin/env python3
"""
RecipeIndexer.py

Preprocess recipes for FAISS retrieval:
1. Chunk recipes into text (title + ingredients)
2. Embed text with sentence-transformers
3. Store embeddings in FAISS (text-only)
4. Keep numeric features in metadata for re-ranking (rating, eco, healthy, vegetarian)
"""

import json
import logging
from pathlib import Path
import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer
import faiss
import pickle
import os

logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

os.environ["TOKENIZERS_PARALLELISM"] = "false"


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
INPUT_FILE = DATA_DIR / "all_recipes_clean.json"
PROCESSED_DIR = DATA_DIR / "processed"
PROCESSED_DIR.mkdir(exist_ok=True, parents=True)

class RecipeIndexer:
    def __init__(self, model_name="paraphrase-multilingual-MiniLM-L12-v2", device="cpu"):
        self.device = device
        self.embedding_model = SentenceTransformer(model_name, device=device)
        self.df = None

    def load_data(self):
        logger.info("Loading recipes...")
        with open(INPUT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.df = pd.DataFrame(data)
        logger.info(f"Loaded {len(self.df)} recipes.")

        if "rating" in self.df.columns:
            median_rating = self.df["rating"].median()
            self.df["rating"] = self.df["rating"].fillna(median_rating)
            logger.info(f"Missing ratings filled with median value: {median_rating:.2f}")


    def create_metadata(self):
        """One metadata row per recipe (non-chunked)."""
        metadata = []
        for _, row in self.df.iterrows():
            ingredients_meta = []
            for ing in row["ingredients"]:
                ingredients_meta.append({
                    "name": ing["ingredient_name"],
                    "quantity": ing["quantity"],
                    "unit": ing["unit"],
                })
            metadata.append({
                "title": row["title"],
                "rating": row["rating"],
                "is_vege": row["is_vege"],
                "total_ecv": row.get("total_ecv"),
                "avg_kcal": row.get("avg_kcal"),
                "avg_fat": row.get("avg_fat"),
                "avg_ecv": row.get("avg_ecv"),
                "ingredients": ingredients_meta,
            })
        return pd.DataFrame(metadata)

    def create_recipe_chunks(self, meta_row, chunk_size=5):
        chunks = []
        title = meta_row.get("title", "")
        if title:
            chunks.append(f"Title: {title}")

        ingredients = [ing["name"] for ing in meta_row.get("ingredients", [])]
        for i in range(0, len(ingredients), chunk_size):
            sub = ", ".join(ingredients[i:i + chunk_size])
            if sub:
                chunks.append(f"Ingredients: {sub}")

        return chunks

    def embed_text_batch(self, texts, batch_size=32):
        embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            emb = self.embedding_model.encode(batch, show_progress_bar=False)
            embeddings.append(emb)
        embeddings = np.vstack(embeddings)
        faiss.normalize_L2(embeddings)  # normalize for cosine similarity
        return embeddings.astype("float32")

    def build_faiss_index(self, vectors):
        logger.info("Building FAISS index...")
        dim = vectors.shape[1]
        index = faiss.IndexFlatIP(dim)
        index.add(vectors)
        logger.info(f"FAISS index built: {index.ntotal} vectors.")
        return index

    def save_outputs(self, metadata, chunk_metadata, text_vectors, index):
        metadata.to_csv(PROCESSED_DIR / "recipes_metadata.csv", index=False)

        with open(PROCESSED_DIR / "chunk_metadata.pkl", "wb") as f:
            pickle.dump(chunk_metadata, f)

        with open(PROCESSED_DIR / "text_vectors.pkl", "wb") as f:
            pickle.dump(text_vectors, f)

        faiss.write_index(index, str(PROCESSED_DIR / "recipes_faiss.index"))

        logger.info(f"Saved processed data to {PROCESSED_DIR}")


    def process(self):
        logger.info("Starting preprocessing...")

        self.load_data()
        metadata = self.create_metadata()

        logger.info("Creating chunks...")
        chunk_texts = []
        chunk_recipe_ids = []
        chunk_metadata = []

        for recipe_id, row in metadata.iterrows():
            chunks = self.create_recipe_chunks(row)

            for i, chunk in enumerate(chunks):
                chunk_texts.append(chunk)
                chunk_recipe_ids.append(recipe_id)
                chunk_metadata.append({
                    "global_chunk_id": len(chunk_metadata),
                    "recipe_id": recipe_id,
                    "chunk_id": i,
                    "text": chunk
                })

        # Embed text only
        text_vectors = self.embed_text_batch(chunk_texts)

        # Build FAISS index
        index = self.build_faiss_index(text_vectors)

        # Save all outputs
        self.save_outputs(metadata, chunk_metadata, text_vectors, index)

        logger.info("Preprocessing completed successfully!")


if __name__ == "__main__":
    RecipeIndexer().process()
