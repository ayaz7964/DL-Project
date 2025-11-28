# # uvicorn main:app --reload --port 8000
    # .\venv\Scripts\activate

# from fastapi import FastAPI, UploadFile, File
# from pydantic import BaseModel
# from rag.pipeline import add_pdf_to_db, generate_answer
# import os

# app = FastAPI()

# from fastapi.middleware.cors import CORSMiddleware

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],   
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# UPLOAD_DIR = "send_files"
# os.makedirs(UPLOAD_DIR, exist_ok=True)

# # --- NEW MODEL ---
# class QueryRequest(BaseModel):
#     query: str


# @app.post("/upload_pdf")
# async def upload_pdf(file: UploadFile = File(...)):
#     file_path = os.path.join(UPLOAD_DIR, file.filename)

#     with open(file_path, "wb") as f:
#         f.write(await file.read())

#     add_pdf_to_db(file_path)

#     return {"message": "PDF added to RAG database"}


# @app.post("/ask")
# async def ask_question(request: QueryRequest):
#     answer = generate_answer(request.query)
#     return {"answer": answer}

# # main.py
# from fastapi import FastAPI, UploadFile, File
# from fastapi.middleware.cors import CORSMiddleware
# from pydantic import BaseModel
# from rag.pipeline_ingest import ingest_all
# from rag.pipeline import generate_answer
# import os
# from apscheduler.schedulers.background import BackgroundScheduler

# app = FastAPI()
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# UPLOAD_DIR = "send_files"
# os.makedirs(UPLOAD_DIR, exist_ok=True)

# class QueryRequest(BaseModel):
#     query: str

# @app.on_event("startup")
# def startup_event():
#     # Run initial ingestion at startup (can be heavy)
#     print("Starting initial ingestion...")
#     try:
#         ingest_all()
#     except Exception as e:
#         print("Initial ingest failed:", e)

#     # Schedule recurrent ingestion every 12 hours
#     scheduler = BackgroundScheduler()
#     scheduler.add_job(func=ingest_all, trigger="interval", hours=12, id="ingest_job", replace_existing=True)
#     scheduler.start()
#     print("Scheduler started (ingest every 12 hours).")

# @app.post("/upload_pdf")
# async def upload_pdf(file: UploadFile = File(...)):
#     file_path = os.path.join(UPLOAD_DIR, file.filename)
#     with open(file_path, "wb") as f:
#         f.write(await file.read())
#     # Optionally ingest this PDF immediately
#     from rag.pdf_loader import extract_pdf_with_headings
#     from rag.chunker import chunk_documents
#     from rag.embeddings import embed_texts
#     from rag.chroma_db import collection
#     docs = extract_pdf_with_headings(file_path)
#     chunks = chunk_documents(docs)
#     if chunks:
#         ids = [c["id"] for c in chunks]
#         txts = [c["document"] for c in chunks]
#         metas = [c["metadata"] for c in chunks]
#         embs = embed_texts(txts)
#         collection.add(ids=ids, documents=txts, embeddings=embs, metadatas=metas)
#     return {"message": "uploaded and ingested"}

# @app.post("/ask")
# async def ask_question(req: QueryRequest):
#     return {"answer": generate_answer(req.query)}




   

# main.py
import os
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# --- RAG modules ---
from rag.pipeline_ingest import ingest_all
from rag.pipeline import generate_answer
from rag.pdf_loader import extract_pdf_with_headings
from rag.chunker import chunk_documents
from rag.embeddings import embed_texts
from rag.chroma_db import collection, add_in_batches

# --- Scheduler ---
from apscheduler.schedulers.background import BackgroundScheduler


# ---------------------------------------------------
# FASTAPI CONFIG
# ---------------------------------------------------
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # React works
    allow_credentials=True,
    allow_methods=["*"],   
    allow_headers=["*"],
)

UPLOAD_DIR = "send_files"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ---------------------------------------------------
# REQUEST MODEL FOR /ask
# ---------------------------------------------------
class QueryRequest(BaseModel):
    query: str


# ---------------------------------------------------
# STARTUP INGESTION (runs ONCE)
# ---------------------------------------------------
@app.on_event("startup")
def startup_event():
    print("🚀 Starting initial ingestion...")

    try:
        ingest_all()
        print("✔ Initial ingestion complete.")
    except Exception as e:
        print("❌ Initial ingest failed:", e)

    scheduler = BackgroundScheduler()
    scheduler.add_job(
        func=ingest_all,
        trigger="interval",
        hours=12,
        id="ingest_job",
        replace_existing=True
    )
    scheduler.start()

    print("⏱ Background scheduler started (every 12 hours).")


# ---------------------------------------------------
# ENDPOINT: UPLOAD PDF → ADD TO RAG DB
# ---------------------------------------------------
@app.post("/upload_pdf")
async def upload_pdf(file: UploadFile = File(...)):
    file_path = os.path.join(UPLOAD_DIR, file.filename)

    with open(file_path, "wb") as f:
        f.write(await file.read())

    # Extract → Chunk → Embed → Store
    docs = extract_pdf_with_headings(file_path)
    chunks = chunk_documents(docs)

    if chunks:
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

        return {"message": "PDF uploaded & ingested successfully"}

    return {"message": "PDF uploaded but no readable text found"}


# ---------------------------------------------------
# ENDPOINT: /ask (React frontend calls this)
# ---------------------------------------------------
@app.post("/ask")
async def ask_question(req: QueryRequest):
    answer = generate_answer(req.query)
    return {"answer": answer}


# ---------------------------------------------------
# HEALTH CHECK (React may call this)
# ---------------------------------------------------
@app.get("/")
def root():
    return {"status": "backend running", "docs_in_db": collection.count()}
    
