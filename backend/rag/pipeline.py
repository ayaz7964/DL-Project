
# from .chroma_db import collection
# from sentence_transformers import SentenceTransformer
# from PyPDF2 import PdfReader
# from transformers import pipeline

# # Load embedding model ONCE
# embedder = SentenceTransformer("all-MiniLM-L6-v2")

# # Load HF LLM ONCE (VERY IMPORTANT)
# generator = pipeline(
#     "text-generation",
#     model="Qwen/Qwen2.5-0.5B-Instruct",
#     device="cpu"  # use "cuda:0" if you have GPU
# ) 

# def add_pdf_to_db(file_path):
#     reader = PdfReader(file_path)
#     text = ""

#     for page in reader.pages:
#         page_text = page.extract_text()
#         if page_text:
#             text += page_text + "\n"

#     chunks = text.split("\n\n")
#     embeddings = embedder.encode(chunks).tolist()
#     ids = [f"doc_{i}" for i in range(len(chunks))]

#     collection.add(
#         ids=ids,
#         documents=chunks,
#         embeddings=embeddings
#     )


# def generate_answer(query):
#     # Step 1: Embed question
#     embedding = embedder.encode([query]).tolist()[0]

#     # Step 2: Retrieve context
#     results = collection.query(
#         query_embeddings=[embedding],
#         n_results=3
#     )

#     context = ""
#     for doc_list in results["documents"]:
#         for doc in doc_list:
#             context += doc + "\n"

#     prompt = f"Context:\n{context}\n\nQuestion: {query}\nAnswer:"

#     # Step 3: Use GPT-2-XL to generate answer
#     output = generator(prompt, max_length=200, num_return_sequences=1)[0]["generated_text"]
    
#     query = "What is SIBAU admission policy?"
#     print('query about admission policies',collection.query(query_embeddings=embedder.encode([query]).tolist(), n_results=5))


#     return output
 

 # rag/pipeline.py
import os
from dotenv import load_dotenv
from openai import OpenAI
from .chroma_db import collection
from .embeddings import embed_text

# Load env so OPENAI_API_KEY / OPENAI_MODEL are picked up
load_dotenv()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL")  # optional for Azure / custom proxy
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Create client once; raise early if key is missing so the API caller sees a clear error
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is not set. Add it to backend/.env or your environment.")

client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)

def build_prompt(question, contexts):
    """
    contexts: list[str] highest-scoring retrieved chunks
    """
    numbered_ctx = "\n".join(f"{i+1}. {c}" for i, c in enumerate(contexts, start=1))
    system_msg = (
        "You are SibaSol assistant. Use only the provided context to answer.\n"
        "- Synthesize across snippets instead of repeating them.\n"
        "- Be concise and natural (2-6 sentences).\n"
        "- If something important is missing, say what is unknown rather than guessing."
    )
    user_msg = (
        f"QUESTION: {question}\n\n"
        f"CONTEXT:\n{numbered_ctx}\n\n"
        "Write a helpful answer."
    )
    return [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_msg},
    ]

def generate_answer(question, top_k=5):
    # 1) embed query
    q_emb = embed_text(question)
    # 2) retrieve
    res = collection.query(query_embeddings=[q_emb], n_results=top_k)
    # results structure: {'ids': [...], 'distances': [...], 'documents': [[...]]}
    docs = []
    seen = set()
    for dlist in res.get("documents", []):
        for d in dlist:
            if d not in seen:
                docs.append(d)
                seen.add(d)
    # If nothing retrieved, quick message
    if not docs:
        return "I don't have any information about that in the knowledge base."

    # 3) Build prompt from top pieces
    messages = build_prompt(question, docs[:top_k])

    # 4) Generate via OpenAI
    resp = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=messages,
        temperature=0.35,
        max_tokens=320,
    )
    return resp.choices[0].message.content.strip()
