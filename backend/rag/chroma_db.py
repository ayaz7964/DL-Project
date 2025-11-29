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

# Default batch size for collection.add (Chroma caps batch size ~166)
DEFAULT_BATCH_SIZE = int(os.getenv("CHROMA_BATCH_SIZE", "100"))


def add_in_batches(ids, documents, embeddings, metadatas=None, batch_size=DEFAULT_BATCH_SIZE, progress=False, upsert=False):
    """
    Utility to avoid Chroma's max batch size errors by splitting large writes.
    Uses upsert when requested to avoid duplicate-id errors.
    """
    total = len(ids)
    for start in range(0, total, batch_size):
        end = start + batch_size
        payload = dict(
            ids=ids[start:end],
            documents=documents[start:end],
            embeddings=embeddings[start:end] if embeddings is not None else None,
            metadatas=metadatas[start:end] if metadatas is not None else None,
        )
        if upsert and hasattr(collection, "upsert"):
            collection.upsert(**payload)
        else:
            collection.add(**payload)
        if progress:
            print(f"[ingest] added {min(end, total)}/{total} records")
