import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.Retriever import RecipeRetriever

retriever = RecipeRetriever()
query = "J'aime les repas sucré..."
response = retriever.retrieve_recipes(query)
print(response)