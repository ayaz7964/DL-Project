
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
from typing import List, Dict, Any
import numpy as np
from dotenv import load_dotenv   
from openai import OpenAI
from .chroma_db import collection
from .embeddings import embed_text, embed_texts
from .scraper_web import scrape_page
from .scraper_facebook import fetch_facebook_posts

# Load env so OPENAI_API_KEY / OPENAI_MODEL are picked up
load_dotenv()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL")  # optional for Azure / custom proxy
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Create client once; raise early if key is missing so the API caller sees a clear error
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is not set. Add it to backend/.env or your environment.")

client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)

# Live web/FB settings
LIVE_WEB_URLS = [
    u.strip()
    for u in os.getenv(
        "LIVE_WEB_URLS",
        "https://www.iba-suk.edu.pk/,https://www.iba-suk.edu.pk/announcements"
    ).split(",")
    if u.strip()
]
MAX_LIVE_CONTEXT = int(os.getenv("MAX_LIVE_CONTEXT", "3"))

def _format_source(meta: Dict[str, Any]) -> str:
    """
    Turn metadata into a friendly source string.
    """
    if not meta:
        return "unknown source"
    parts = []
    src_type = meta.get("source")
    file_name = meta.get("file")
    url = meta.get("url")
    heading = meta.get("heading")
    if src_type:
        parts.append(str(src_type))
    if file_name:
        parts.append(os.path.basename(str(file_name)))
    if url and not file_name:
        parts.append(str(url))
    if heading:
        parts.append(f"section: {heading}")
    return " | ".join(parts) if parts else "unknown source"


def _history_messages(history: List[Dict[str, Any]], limit: int = 10):
    """
    Convert a list of {role, text} dicts to OpenAI chat messages, keeping the last N.
    """
    if not history:
        return []
    trimmed = history[-limit:]
    msgs = []
    for h in trimmed:
        role = h.get("role")
        txt = h.get("text") or ""
        if role not in ("user", "assistant") or not txt:
            continue
        msgs.append({"role": role, "content": txt})
    return msgs


def build_prompt(question: str, contexts: List[Dict[str, Any]], history: List[Dict[str, Any]] = None):
    """
    contexts: list of dicts with keys document, metadata
    """
    entries = []
    for i, item in enumerate(contexts, start=1):
        doc = item.get("document", "")
        meta = item.get("metadata", {}) or {}
        src = _format_source(meta)
        entries.append(f"[{i}] {doc}\n(Source: {src})")
    numbered_ctx = "\n\n".join(entries)
    system_msg = (
        "You are the official SIBAU assistant. Use only the provided context (RAG KB + fresh web/social samples) to answer.\n"
        "- Prefer the knowledge base; use live web/FB snippets to confirm recency.\n"
        "- If sources conflict, state the difference and prefer the KB unless recency is clear.\n"
        "- Synthesize across snippets instead of repeating them.\n"
        "- Be concise and natural (2-6 sentences) and speak like a helpful university representative.\n"
        "- Do NOT mention the words 'context', 'snippet', or that you are using provided text; just answer directly.\n"
        "- If something important is missing, say what is unknown rather than guessing."
    )
    user_msg = (
        f"QUESTION: {question}\n\n"
        f"CONTEXT:\n{numbered_ctx}\n\n"
        "Write a helpful answer."
    )
    messages = [{"role": "system", "content": system_msg}]
    messages.extend(_history_messages(history or []))
    messages.append({"role": "user", "content": user_msg})
    return messages

def _retrieve(q_emb, top_k: int = 5, fetch_k: int = None, max_distance: float = None):
    """
    Retrieve candidates from Chroma with metadata and distances, then sort and deduplicate.
    """
    fetch_k = fetch_k or max(top_k * 3, top_k + 2)
    max_distance = max_distance if max_distance is not None else 0.4  # cosine distance; lower is closer
    res = collection.query(
        query_embeddings=[q_emb],
        n_results=fetch_k,
        include=["documents", "metadatas", "distances"],
    )
    candidates = []
    for docs, metas, dists in zip(
        res.get("documents", []),
        res.get("metadatas", []),
        res.get("distances", []),
    ):
        for doc, meta, dist in zip(docs, metas, dists):
            dval = float(dist)
            if dval > max_distance:
                continue
            candidates.append(
                {"document": doc, "metadata": meta or {}, "distance": dval}
            )
    # sort by distance (lower = closer for cosine in Chroma)
    candidates.sort(key=lambda x: x["distance"])

    # Deduplicate identical text to avoid prompt bloat
    seen_docs = set()
    unique = []
    for c in candidates:
        dtext = c["document"]
        if dtext in seen_docs:
            continue
        seen_docs.add(dtext)
        unique.append(c)
        if len(unique) >= top_k:
            break
    return unique


def _fetch_live_candidates(q_emb, max_items: int = MAX_LIVE_CONTEXT, min_sim: float = 0.3):
    """
    Fetch fresh snippets from SIBA website and Facebook, rank by cosine similarity to the query embedding.
    """
    if max_items <= 0:
        return []

    docs = []
    # target a handful of key pages (announcements / homepage)
    for url in LIVE_WEB_URLS:
        docs.extend(scrape_page(url))
    docs.extend(fetch_facebook_posts())

    texts = []
    metas = []
    for d in docs:
        content = d.get("content", "")
        if not content or len(content) < 30:
            continue
        texts.append(content)
        metas.append({
            "source": d.get("source") or "live_web",
            "url": d.get("url"),
            "file": d.get("file"),
            "heading": d.get("heading"),
            "subheading": d.get("subheading"),
        })

    if not texts:
        return []

    embs = embed_texts(texts)
    q_vec = np.array(q_emb)
    candidates = []

    for emb, text, meta in zip(embs, texts, metas):
        e_vec = np.array(emb)
        denom = (np.linalg.norm(q_vec) * np.linalg.norm(e_vec)) + 1e-9
        sim = float(np.dot(q_vec, e_vec) / denom)
        if sim < min_sim:
            continue
        candidates.append({"document": text, "metadata": meta, "sim": sim})

    # sort by similarity (higher better)
    candidates.sort(key=lambda x: x["sim"], reverse=True)

    # deduplicate text
    unique = []
    seen = set()
    for c in candidates:
        dtext = c["document"]
        if dtext in seen:
            continue
        seen.add(dtext)
        unique.append(c)
        if len(unique) >= max_items:
            break
    return unique


def _format_references(contexts: List[Dict[str, Any]]) -> str:
    """
    Produce a short natural-language sources string.
    """
    seen = set()
    refs = []
    for c in contexts:
        ref = _format_source(c.get("metadata", {}))
        if ref and ref not in seen:
            refs.append(ref)
            seen.add(ref)
    if not refs:
        return ""
    if len(refs) == 1:
        return f"Source: {refs[0]}"
    return "Sources: " + "; ".join(refs)


def generate_answer(question, top_k=5, history=None):
    # 1) embed query
    q_emb = embed_text(question)

    # 2) retrieve from KB with rerank/dedup
    kb_contexts = _retrieve(q_emb, top_k=top_k)

    # 3) if KB empty, fetch fresh web/social snippets and rank
    live_contexts = []
    if not kb_contexts:
        live_contexts = _fetch_live_candidates(q_emb, max_items=MAX_LIVE_CONTEXT)

    # decide contexts: prefer KB; otherwise use live; otherwise none
    if kb_contexts:
        contexts = kb_contexts
    elif live_contexts:
        contexts = live_contexts
    else:
        contexts = []

    # If nothing retrieved, use guarded general response scoped to SIBAU
    if not contexts:
        fallback_messages = [
            {
                "role": "system",
                "content": (
                    "You are the official SIBAU assistant. Answer only about Sukkur IBA University and its operations. "
                    "If you do not know something about SIBAU, say you don't have that information. "
                    "Greet politely and stay on SIBAU topics."
                ),
            },
        ]
        fallback_messages.extend(_history_messages(history or []))
        fallback_messages.append({"role": "user", "content": question})
        resp = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=fallback_messages,
            temperature=0.35,
            max_tokens=200,
        )
        return resp.choices[0].message.content.strip()

    # 4) Build prompt from top pieces
    messages = build_prompt(question, contexts, history=history)

    # 5) Generate via OpenAI
    resp = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=messages,
        temperature=0.35,
        max_tokens=320,
    )
    answer = resp.choices[0].message.content.strip()

    # Append references in natural language so the user knows where it came from
    ref_text = _format_references(contexts)
    if ref_text:
        return f"{answer}\n\n{ref_text}"
    return answer
