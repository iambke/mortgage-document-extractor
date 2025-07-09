from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import pytesseract
import cv2
import numpy as np
import sqlite3
import spacy
import re
from pdf2image import convert_from_bytes
import logging

# Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files (frontend)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def read_index():
    return FileResponse("static/index.html")

# spaCy
nlp = spacy.load("en_core_web_sm")

# SQLite
conn = sqlite3.connect("extracted_data.db", check_same_thread=False)
cur = conn.cursor()
cur.execute("""
    CREATE TABLE IF NOT EXISTS documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        borrower_name TEXT,
        loan_amount TEXT,
        property_address TEXT
    )
""")
conn.commit()

# Check for mortgage relevance
def is_mortgage_document(text: str) -> bool:
    keywords = [
        "mortgage", "borrower", "loan amount", "property", "lender",
        "principal sum", "secured", "monthly payment", "deed", "address"
    ]
    return sum(1 for k in keywords if k.lower() in text.lower()) >= 2

# Check if extracted entities make sense
def is_valid_mortgage_data(text, name, amount, address):
    if name == "Not found" or len(name.split()) < 2:
        return False
    if not re.match(r'^\$\d{1,3}(?:,\d{3})*(?:\.\d{2})?$', amount):
        return False
    if address == "Not found" or len(address.split()) < 4:
        return False
    return True

# Preprocess images
def preprocess_image(img_bytes):
    img = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Image decoding failed")
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, threshed = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
    return threshed

# Extract name, amount, address
def extract_entities(text):
    doc = nlp(text)
    name, amount, address = None, None, None

    for ent in doc.ents:
        if ent.label_ == "PERSON" and not name:
            name = ent.text.strip()

    if not name:
        match = re.search(r'between\s+([A-Z][a-zA-Z\s]+?),', text)
        if match:
            name = match.group(1).strip()

    match = re.search(r'principal sum of\s+\$[\d,]+(?:\.\d{2})?', text, re.IGNORECASE)
    if match:
        amount = match.group(0).split("of")[-1].strip()
    else:
        match = re.search(r'\$\d[\d,]*(?:\.\d{2})?', text)
        if match:
            amount = match.group(0)

    lines = re.sub(r'\n+', '\n', text.strip()).splitlines()
    for i, line in enumerate(lines):
        if 'located at' in line.lower():
            addr_lines = []
            for j in range(i + 1, min(i + 5, len(lines))):
                part = lines[j].strip()
                if part:
                    addr_lines.append(part)
            if addr_lines:
                address = ', '.join(addr_lines)
                break

    if not address:
        for ent in doc.ents:
            if ent.label_ in ["GPE", "LOC"] and not address:
                address = ent.text.strip()

    if address:
        zip_match = re.search(r'\d{5}(?:-\d{4})?', address)
        if zip_match:
            address = address[:zip_match.end()]
        else:
            address = re.split(r'\bIN WITNESS\b|\bNOW THEREFORE\b', address, flags=re.IGNORECASE)[0]
        address = re.sub(r'[^\w\s.,#-]', '', address)
        address = re.sub(r',+', ',', address).strip()

    return name or "Not found", amount or "Not found", address or "Not found"

# Main route
@app.post("/extract/")
async def extract(file: UploadFile = File(...)):
    ext = file.filename.split('.')[-1].lower()
    if ext not in ['jpg', 'jpeg', 'png', 'pdf']:
        raise HTTPException(status_code=400, detail="Only JPG, PNG, or PDF files are allowed")

    file_bytes = await file.read()

    try:
        if ext == 'pdf':
            images = convert_from_bytes(file_bytes)
            if not images:
                raise ValueError("Empty PDF")
            img = np.array(images[0])
            img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        else:
            img = preprocess_image(file_bytes)

        text = pytesseract.image_to_string(img)
        logger.info(f"OCR Output (first 500 chars):\n{text[:500]}")

        if not is_mortgage_document(text):
            raise HTTPException(status_code=400, detail="Not a mortgage-related document.")

        name, amount, address = extract_entities(text)

        if not is_valid_mortgage_data(text, name, amount, address):
            raise HTTPException(status_code=422, detail="Document doesn't contain valid mortgage data.")

        cur.execute("INSERT INTO documents (borrower_name, loan_amount, property_address) VALUES (?, ?, ?)",
                    (name, amount, address))
        doc_id = cur.lastrowid
        conn.commit()

        return {
            "id": doc_id,
            "borrower_name": name,
            "loan_amount": amount,
            "property_address": address
        }

    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to process the document")

# View by ID
@app.get("/data/{doc_id}")
async def get_document(doc_id: int):
    cur.execute("SELECT * FROM documents WHERE id = ?", (doc_id,))
    row = cur.fetchone()
    if row:
        return {
            "id": row[0],
            "borrower_name": row[1],
            "loan_amount": row[2],
            "property_address": row[3]
        }
    else:
        raise HTTPException(status_code=404, detail="Document not found")
