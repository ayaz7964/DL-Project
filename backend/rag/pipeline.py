
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
from .chroma_db import collection
from .embeddings import embed_text
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
import threading
import os

# Load Qwen or other model once (CPU or GPU). replace with your HF model id
MODEL_NAME = "Qwen/Qwen2.5-0.5B-Instruct"  # replace with "Qwen/..." if you installed it
# For Qwen local usage you must have the model weights; adjust MODEL_NAME accordingly.

# Load tokenizer+model once (this may take time on startup)
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForCausalLM.from_pretrained(MODEL_NAME)
generator = pipeline("text-generation", model=model, tokenizer=tokenizer, device=-1)

def build_prompt(question, contexts):
    """
    contexts: list[str] highest-scoring retrieved chunks
    """
    numbered_ctx = "\n".join(f"{i+1}. {c}" for i, c in enumerate(contexts, start=1))
    return (
        "You are SibaSol assistant. Read the context snippets and craft a clear, helpful answer.\n"
        "Guidelines:\n"
        "- Synthesize across snippets; combine details instead of repeating them.\n"
        "- Use the context to infer missing links when it is reasonable; make the reasoning explicit.\n"
        "- Reply in natural language (2-6 sentences). Do not just quote the context.\n"
        "- If key information is missing, say what is unknown instead of guessing.\n\n"
        f"CONTEXT:\n{numbered_ctx}\n\nQUESTION: {question}\nANSWER:"
    )

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
    prompt = build_prompt(question, docs[:top_k])

    # 4) Generate
    gen_out = generator(
        prompt,
        num_return_sequences=1,
        max_new_tokens=256,
        temperature=0.35,
        top_p=0.9,
        do_sample=True,
        return_full_text=False,
    )[0]
    answer = gen_out.get("generated_text", "").strip()
    if not answer:
        # fallback in case the pipeline still includes the prompt
        raw = gen_out.get("generated_text", "") if isinstance(gen_out, dict) else str(gen_out)
        if "ANSWER:" in raw:
            return raw.split("ANSWER:")[-1].strip()
    return answer
