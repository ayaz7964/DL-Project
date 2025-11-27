from .scraper_web import scrape_page
from .scraper_facebook import fetch_facebook_posts
from .pdf_loader import extract_pdf
from .chunker import chunk_docs
from .embeddings import embed
from .chroma_db import collection
import glob
import uuid

def ingest_all():
    final_docs = []

    urls = [
        # ADD YOUR UNIVERSITY LINKS HERE
        "https://example.edu/admission",
        "https://example.edu/fee-structure"
    ]

    for url in urls:
        final_docs += scrape_page(url)

    final_docs += fetch_facebook_posts()

    for pdf in glob.glob("data/pdfs/*.pdf"):
        final_docs += extract_pdf(pdf)

    chunks = chunk_docs(final_docs)

    for d in chunks:
        collection.add(
            documents=[d["content"]],
            embeddings=[embed(d["content"])],
            ids=[str(uuid.uuid4())],
            metadatas=[d]
        )

    print("Ingestion completed!")
