"""Download the embedding model."""

from sentence_transformers import SentenceTransformer

print("Downloading all-MiniLM-L6-v2 embedding model...")
print("This may take a few minutes on first download (~90MB)")
print()

model = SentenceTransformer('all-MiniLM-L6-v2')

print("✓ Model downloaded successfully!")
print(f"✓ Embedding dimension: {model.get_sentence_embedding_dimension()}")
print("✓ Model is cached and ready to use")
