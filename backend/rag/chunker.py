# def chunk_docs(docs, max_len=500):
#     chunks = []
#     for d in docs:
#         text = d["content"]

#         if len(text) <= max_len:
#             chunks.append(d)
#         else:
#             for i in range(0, len(text), max_len):
#                 new_doc = d.copy()
#                 new_doc["content"] = text[i:i+max_len]
#                 chunks.append(new_doc)

#     return chunks


# rag/chunker.py
import uuid
from typing import Dict, Any

# Chroma only accepts metadata values of type str/int/float/bool.
# We drop None values and stringify anything else to prevent ingest errors.
ALLOWED_META_TYPES = (str, int, float, bool)


def _clean_metadata(meta: Dict[str, Any]) -> Dict[str, Any]:
    cleaned = {}
    for key, value in meta.items():
        if value is None:
            continue
        if isinstance(value, ALLOWED_META_TYPES):
            cleaned[key] = value
        else:
            cleaned[key] = str(value)
    return cleaned


def chunk_text_with_meta(doc, chunk_size=600, overlap=100):
    """
    doc: dict with keys heading, subheading, content, source, file/url
    returns list of chunk dicts including metadata
    """
    text = doc.get("content", "")
    if not text:
        return []

    chunks = []
    start = 0
    length = len(text)
    while start < length:
        end = min(start + chunk_size, length)
        chunk_text = text[start:end].strip()
        if chunk_text:
            raw_meta = {
                "heading": doc.get("heading"),
                "subheading": doc.get("subheading"),
                "source": doc.get("source") or "unknown",
                "file": doc.get("file"),
                "url": doc.get("url"),
            }
            chunks.append({
                "id": str(uuid.uuid4()),
                "document": chunk_text,
                "metadata": _clean_metadata(raw_meta),
            })
        start = end - overlap  # move with overlap
        if start < 0:
            start = 0
        if end == length:
            break
    return chunks


def chunk_documents(docs, chunk_size=600, overlap=100):
    all_chunks = []
    for d in docs:
        all_chunks.extend(chunk_text_with_meta(d, chunk_size=chunk_size, overlap=overlap))
    return all_chunks
