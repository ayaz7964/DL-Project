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
            chunks.append({
                "id": str(uuid.uuid4()),
                "document": chunk_text,
                "metadata": {
                    "heading": doc.get("heading"),
                    "subheading": doc.get("subheading"),
                    "source": doc.get("source"),
                    "file": doc.get("file"),
                    "url": doc.get("url")
                }
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
