# rag/chroma_db.py

from chromadb import PersistentClient

# Create a persistent ChromaDB client
chroma_client = PersistentClient(path="chroma_storage")

# Create or load the collection
collection = chroma_client.get_or_create_collection(
    name="documents",
    metadata={"hnsw:space": "cosine"}
)
