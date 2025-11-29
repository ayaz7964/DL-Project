import os
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from apscheduler.schedulers.background import BackgroundScheduler

# RAG modules
from rag.pipeline_ingest import ingest_if_changed, update_manifest_snapshot
from rag.pipeline import generate_answer
from rag.pdf_loader import extract_pdf_with_headings
from rag.chunker import chunk_documents
from rag.embeddings import embed_texts
from rag.chroma_db import collection, add_in_batches

# ---------------------------------------------------
# FASTAPI CONFIG
# ---------------------------------------------------
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "send_files"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ---------------------------------------------------
# REQUEST MODEL FOR /ask
# ---------------------------------------------------
class QueryTurn(BaseModel):
    role: str
    text: str

class QueryRequest(BaseModel):
    query: str
    history: Optional[List[QueryTurn]] = None


# ---------------------------------------------------
# STARTUP INGESTION (only on data change)
# ---------------------------------------------------
@app.on_event("startup")
def startup_event():
    print("Starting ingestion check...")

    try:
        changed = ingest_if_changed()
        if changed:
            print("Initial ingest complete (changes detected).")
        else:
            print("No changes detected; using existing Chroma data.")
    except Exception as e:
        print("Initial ingest failed:", e)

    scheduler = BackgroundScheduler()
    scheduler.add_job(
        func=ingest_if_changed,
        trigger="interval",
        hours=12,
        id="ingest_job",
        replace_existing=True,
    )
    scheduler.start()

    print("Background scheduler started (every 12 hours, only ingests on data change).")


# ---------------------------------------------------
# ENDPOINT: UPLOAD PDF + ADD TO RAG DB
# ---------------------------------------------------
@app.post("/upload_pdf")
async def upload_pdf(file: UploadFile = File(...)):
    file_path = os.path.join(UPLOAD_DIR, file.filename)

    with open(file_path, "wb") as f:
        f.write(await file.read())

    docs = extract_pdf_with_headings(file_path)
    chunks = chunk_documents(docs)

    if not chunks:
        update_manifest_snapshot(pdfs_dir="data/pdfs", send_dir=UPLOAD_DIR)
        return {"message": "PDF uploaded but no readable text found"}

    ids = [c["id"] for c in chunks]
    txts = [c["document"] for c in chunks]
    metas = [c["metadata"] for c in chunks]
    embs = embed_texts(txts)

    add_in_batches(
        ids=ids,
        documents=txts,
        embeddings=embs,
        metadatas=metas,
    )

    # keep manifest aligned so future startups skip re-ingest
    update_manifest_snapshot(pdfs_dir="data/pdfs", send_dir=UPLOAD_DIR)

    return {"message": "PDF uploaded & ingested successfully"}


# ---------------------------------------------------
# ENDPOINT: /ask (React frontend calls this)
# ---------------------------------------------------
@app.post("/ask")
async def ask_question(req: QueryRequest):
    history = None
    if req.history:
        history = [{"role": h.role, "text": h.text} for h in req.history if h.text]
    answer = generate_answer(req.query, history=history)
    return {"answer": answer}


# ---------------------------------------------------
# HEALTH CHECK (React may call this)
# ---------------------------------------------------
@app.get("/")
def root():
    return {"status": "backend running", "docs_in_db": collection.count()}
