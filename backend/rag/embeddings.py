# from openai import OpenAI
# from dotenv import load_dotenv
# import os

# load_dotenv()
# client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# def embed(text: str):
#     res = client.embeddings.create(
#         model="text-embedding-3-large",
#         input=text
#     )
#     return res.data[0].embedding


# rag/embeddings.py
from sentence_transformers import SentenceTransformer

# load once at import time (fast, small & effective)
EMBED_MODEL_NAME = "all-MiniLM-L6-v2"
embedder = SentenceTransformer(EMBED_MODEL_NAME)

def embed_texts(texts):
    """
    texts: list[str]
    returns: list[list[float]] embeddings
    """
    if not texts:
        return []
    embs = embedder.encode(texts, show_progress_bar=False, convert_to_numpy=True)
    return embs.tolist()

def embed_text(text):
    return embed_texts([text])[0]
