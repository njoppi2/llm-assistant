from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
import httpx
from pdf2docx import Converter
from docx import Document
import io
import tempfile
import docx2txt
import mammoth
app = FastAPI()

class Query(BaseModel):
    question: str
    prompt: str
    document_url: str

def download_pdf(url):
    response = httpx.get(url)
    response.raise_for_status()
    return io.BytesIO(response.content)

def convert_pdf_to_docx(pdf_stream, docx_path):
    # with open("temp.pdf", "wb") as f:
    #     f.write(pdf_stream.read())
    # cv = Converter("temp.pdf")
    # cv.convert(docx_path)
    # cv.close()
    pass

import subprocess

def extract_text_from_docx(docx_path):
    results = {}

    # Method 1: Using python-docx with enhanced filtering
    try:
        doc = Document(docx_path)
        text_python_docx = []
        header_footer_styles = ['Header', 'Footer', 'Header Char', 'Footer Char']
        for para in doc.paragraphs:
            if para.style.name not in header_footer_styles and not para.text.strip().startswith(('Page', 'Header', 'Footer')):
                text_python_docx.append(para.text)
        results["python_docx"] = '\n'.join(text_python_docx)
    except Exception as e:
        results["python_docx"] = f"Failed with error: {str(e)}"

    # Method 2: Using docx2txt with basic filtering
    try:
        text_docx2txt = docx2txt.process(docx_path)
        filtered_text_docx2txt = "\n".join([line for line in text_docx2txt.splitlines() if not line.strip().startswith(('Page', 'Header', 'Footer'))])
        results["docx2txt"] = filtered_text_docx2txt
    except Exception as e:
        results["docx2txt"] = f"Failed with error: {str(e)}"

    # Method 3: Using mammoth with basic filtering
    try:
        with open(docx_path, "rb") as docx_file:
            result = mammoth.extract_raw_text(docx_file)
            text_mammoth = result.value
            filtered_text_mammoth = "\n".join([line for line in text_mammoth.splitlines() if not line.strip().startswith(('Page', 'Header', 'Footer'))])
            results["mammoth"] = filtered_text_mammoth
    except Exception as e:
        results["mammoth"] = f"Failed with error: {str(e)}"

    # Method 4: Using LibreOffice soffice to convert DOCX to plain text
    try:
        output_txt_path = "output.txt"
        subprocess.run(['soffice', '--headless', '--convert-to', 'txt', '--outdir', '.', docx_path], check=True)
        with open(output_txt_path, 'r') as file:
            text_soffice = file.read()
        results["soffice"] = text_soffice
    except Exception as e:
        results["soffice"] = f"Failed with error: {str(e)}"

    return results


@app.post("/process-question")
async def process_question(query: Query):
    # Download the PDF
    try:
        pdf_stream = download_pdf(query.document_url)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch PDF: {str(e)}")

    # Convert PDF to DOCX
    try:
        docx_path = "output.docx"
        convert_pdf_to_docx(pdf_stream, docx_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to convert PDF to DOCX: {str(e)}")

    # Extract text from DOCX
    try:
        text = extract_text_from_docx(docx_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to extract text from DOCX: {str(e)}")

    # Print the extracted text for debugging
    print(f"Extracted text:\n{text[:1000]}")  # Print the first 1000 characters for brevity

    return {
        "question": query.question,
        "prompt": query.prompt,
        "document_url": query.document_url,
        "answer": text
    }

@app.get("/")
async def read_index():
    return FileResponse('static/index.html')
