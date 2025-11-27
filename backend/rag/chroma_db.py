# # rag/chroma_db.py

# from chromadb import PersistentClient

# # Create a persistent ChromaDB client
# chroma_client = PersistentClient(path="chroma_storage")

# # Create or load the collection
# collection = chroma_client.get_or_create_collection(
#     name="documents",
#     metadata={"hnsw:space": "cosine"}
# )
# print('collection counts are ' ,collection.count()) 

# rag/chroma_db.py
from chromadb import PersistentClient
from chromadb.config import Settings
import os

# ensure storage dir exists
os.makedirs("chroma_storage", exist_ok=True)

# PersistentClient for chroma v0.4.22
chroma_client = PersistentClient(path="chroma_storage")

# Single collection used across pipeline
COLLECTION_NAME = "siba_knowledge"

collection = chroma_client.get_or_create_collection(
    name=COLLECTION_NAME,
    metadata={"hnsw:space": "cosine"}
)
