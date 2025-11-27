# rag/pipeline.py

from .chroma_db import collection
from sentence_transformers import SentenceTransformer
from PyPDF2 import PdfReader

model = SentenceTransformer("all-MiniLM-L6-v2")

def add_pdf_to_db(file_path):
    reader = PdfReader(file_path)
    text = ""

    for page in reader.pages:
        text += page.extract_text() + "\n"

    chunks = text.split("\n\n")
    embeddings = model.encode(chunks).tolist()

    ids = [f"doc_{i}" for i in range(len(chunks))]

    collection.add(
        ids=ids,
        documents=chunks,
        embeddings=embeddings
    )


def generate_answer(query):
    embedding = model.encode([query]).tolist()[0]

    results = collection.query(
        query_embeddings=[embedding],
        n_results=3
    )

    if not results["documents"]:
        return "No relevant information found."

    answer = ""

    for doc_list in results["documents"]:
        for doc in doc_list:
            answer += doc + "\n"

    return answer
