from .embeddings import embed
from .chroma_db import collection
from .llm import llm

def answer_query(query):
    q_emb = embed(query)

    results = collection.query(
        query_embeddings=[q_emb],
        n_results=5
    )

    context = ""
    for doc in results["documents"][0]:
        context += doc + "\n\n"

    prompt = f"""
    You are SibaSol AI Assistant.
    Use the context to answer the question.
    If you don't know, say "Not available".

    CONTEXT:
    {context}

    QUESTION: {query}
    """

    return llm(prompt)
