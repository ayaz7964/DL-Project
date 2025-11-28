# from .scraper_web import scrape_page
# from .scraper_facebook import fetch_facebook_posts
# from .pdf_loader import extract_pdf
# from .chunker import chunk_docs
# from .embeddings import embed
# from .chroma_db import collection
# import glob
# import uuid

# def ingest_all():
#     final_docs = []

#     urls = [
#         # ADD YOUR UNIVERSITY LINKS HERE
#         "https://www.iba-suk.edu.pk/",
       
#     ]

#     for url in urls:
#         final_docs += scrape_page(url)

#     final_docs += fetch_facebook_posts()

#     for pdf in glob.glob("data/pdfs/*.pdf"):
#         final_docs += extract_pdf(pdf)

#     chunks = chunk_docs(final_docs)

#     for d in chunks:
#         collection.add(
#             documents=[d["content"]],
#             embeddings=[embed(d["content"])],
#             ids=[str(uuid.uuid4())],
#             metadatas=[d]
#         )

#     print("Ingestion completed!")


# rag/pipeline_ingest.py
from .pdf_loader import extract_pdf_with_headings
from .scraper_web import crawl_and_collect, scrape_page
from .scraper_facebook import fetch_facebook_posts
from .chunker import chunk_documents
from .embeddings import embed_texts
from .chroma_db import collection, add_in_batches
import json
import glob
import os

# put your university pages here
UNIVERSITY_URLS = [
    "https://www.iba-suk.edu.pk/",
   
    # add other section urls
]

MANIFEST_PATH = os.path.join("data", ".ingest_manifest.json")

def _file_signature(paths):
    """
    Build a dict of absolute path -> {mtime, size} for change detection.
    """
    sig = {}
    for p in paths:
        if not os.path.isfile(p):
            continue
        try:
            st = os.stat(p)
            sig[os.path.abspath(p)] = {"mtime": st.st_mtime, "size": st.st_size}
        except OSError:
            continue
    return sig

def _current_manifest(pdfs_dir="data/pdfs", send_dir="send_files"):
    pdfs = glob.glob(os.path.join(pdfs_dir, "*.pdf"))
    send_pdfs = glob.glob(os.path.join(send_dir, "*.pdf")) if os.path.isdir(send_dir) else []
    return _file_signature(pdfs + send_pdfs)

def _load_manifest(path=MANIFEST_PATH):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _save_manifest(manifest, path=MANIFEST_PATH):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

def ingest_needed(pdfs_dir="data/pdfs", send_dir="send_files", manifest_path=MANIFEST_PATH):
    """
    Returns True if files were added/removed/changed since last manifest snapshot.
    """
    current = _current_manifest(pdfs_dir, send_dir)
    previous = _load_manifest(manifest_path)
    return current != previous, current

def ingest_all(pdfs_dir="data/pdfs", scraped_dir="data/scraped", send_dir="send_files"):
    """
    Full run: scrape website + facebook -> parse PDFs -> chunk -> embed -> store in Chroma
    """
    final_docs = []

    # 1) website scraping
    try:
        web_docs = crawl_and_collect(UNIVERSITY_URLS)
        final_docs.extend(web_docs)
    except Exception as e:
        print("website scrape failed", e)

    # 2) facebook
    try:
        fb = fetch_facebook_posts()
        final_docs.extend(fb)
    except Exception as e:
        print("fb scrape failed", e)

    # 3) local PDFs in data/pdfs (and send_files if you want)
    pdf_paths = glob.glob(os.path.join(pdfs_dir, "*.pdf"))
    for p in pdf_paths:
        try:
            pdf_docs = extract_pdf_with_headings(p)
            final_docs.extend(pdf_docs)
        except Exception as e:
            print("pdf parse error", p, e)

    # optionally also scan send_files
    if os.path.isdir(send_dir):
        for p in glob.glob(os.path.join(send_dir, "*.pdf")):
            try:
                final_docs.extend(extract_pdf_with_headings(p))
            except Exception as e:
                print("send_files parse error", p, e)

    # 4) chunking
    chunks = chunk_documents(final_docs, chunk_size=600, overlap=100)
    if not chunks:
        print("No chunks to add.")
        return

    # 5) embed and upsert to chroma
    docs = [c["document"] for c in chunks]
    metadatas = [c["metadata"] for c in chunks]
    ids = [c["id"] for c in chunks]

    embs = embed_texts(docs)
    add_in_batches(
        ids=ids,
        documents=docs,
        embeddings=embs,
        metadatas=metadatas,
    )
    print(f"Ingested {len(ids)} chunks into collection.")


def ingest_if_changed(pdfs_dir="data/pdfs", send_dir="send_files"):
    """
    Run ingest_all only if local PDF files changed since last snapshot.
    """
    needed, snapshot = ingest_needed(pdfs_dir, send_dir)
    if not needed:
        print("No local data changes detected; skipping ingest.")
        return False

    ingest_all(pdfs_dir=pdfs_dir, send_dir=send_dir)
    _save_manifest(snapshot)
    return True


def update_manifest_snapshot(pdfs_dir="data/pdfs", send_dir="send_files"):
    """
    Refresh manifest after manual uploads so future startups don't re-ingest unnecessarily.
    """
    snapshot = _current_manifest(pdfs_dir, send_dir)
    _save_manifest(snapshot)
    return snapshot
