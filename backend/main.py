from fastapi import FastAPI, UploadFile, File
from rag.rag_answer import answer_query
from rag.pipeline_ingest import ingest_all
from rag.pdf_loader import extract_pdf
import os

app = FastAPI()

@app.get("/")
def home():
    return {"status": "SibaSol RAG Backend Running"}

@app.get("/ask")
def ask(query: str):
    return {"answer": answer_query(query)}

@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    path = f"data/pdfs/{file.filename}"
    with open(path, "wb") as f:
        f.write(await file.read())

    docs = extract_pdf(path)
    return {"status": "PDF processed", "chunks": len(docs)}

@app.post("/ingest")
def ingest():
    ingest_all()
    return {"status": "Ingestion Completed"}
