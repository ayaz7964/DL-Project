# uvicorn main:app --reload --port 8000
from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel
from rag.pipeline import add_pdf_to_db, generate_answer
import os

app = FastAPI()

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "send_files"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# --- NEW MODEL ---
class QueryRequest(BaseModel):
    query: str


@app.post("/upload_pdf")
async def upload_pdf(file: UploadFile = File(...)):
    file_path = os.path.join(UPLOAD_DIR, file.filename)

    with open(file_path, "wb") as f:
        f.write(await file.read())

    add_pdf_to_db(file_path)

    return {"message": "PDF added to RAG database"}


@app.post("/ask")
async def ask_question(request: QueryRequest):
    answer = generate_answer(request.query)
    return {"answer": answer}
