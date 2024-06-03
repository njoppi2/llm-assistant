from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI()

class Query(BaseModel):
    question: str
    prompt: str
    document_url: str

@app.post("/process-question")
async def process_question(query: Query):
    # Mocked response
    return {
        "question": query.question,
        "prompt": query.prompt,
        "document_url": query.document_url,
        "answer": "This is a mocked answer."
    }

@app.get("/")
async def read_index():
    return FileResponse('static/index.html')

app.mount("/static", StaticFiles(directory="static"), name="static")
