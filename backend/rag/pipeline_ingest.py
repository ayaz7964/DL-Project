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
import glob
import os

# put your university pages here
UNIVERSITY_URLS = [
    "https://www.iba-suk.edu.pk/",
   
    # add other section urls
]

def ingest_all(pdfs_dir="data/pdfs", scraped_dir="data/scraped"):
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
    send_files_dir = "send_files"
    if os.path.isdir(send_files_dir):
        for p in glob.glob(os.path.join(send_files_dir, "*.pdf")):
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
