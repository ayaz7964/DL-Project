def chunk_docs(docs, max_len=500):
    chunks = []
    for d in docs:
        text = d["content"]

        if len(text) <= max_len:
            chunks.append(d)
        else:
            for i in range(0, len(text), max_len):
                new_doc = d.copy()
                new_doc["content"] = text[i:i+max_len]
                chunks.append(new_doc)

    return chunks
