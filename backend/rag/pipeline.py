from .embeddings import embed
from .chroma_db import chroma_client
from .llm import generate_answer

def answer_question(query):
    # 1. Embed query
    q_emb = embed(query)

    # 2. Search relevant docs
    results = chroma_client.query(
        query_embeddings=[q_emb],
        n_results=5,
    )

    context = ""
    for chunk in results["documents"][0]:
        context += chunk + "\n\n"

    # 3. Build prompt
    prompt = f"""
    You are a university assistant.
    Answer using the context below.
    If you don't know, say you don't know.

    CONTEXT:
    {context}

    QUESTION:
    {query}
    """

    # 4. Generate answer
    return generate_answer(prompt)
