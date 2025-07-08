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

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def read_index():
    return FileResponse("static/index.html")

# Load spaCy model
nlp = spacy.load("en_core_web_sm")

# SQLite setup
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

# Image preprocessing
def preprocess_image(img_bytes):
    img = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, threshed = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
    return threshed

# Entity Extraction
def extract_entities(text):
    doc = nlp(text)
    name, amount, address = None, None, None

    # Borrower Name (spaCy or regex fallback)
    for ent in doc.ents:
        if ent.label_ == "PERSON" and not name:
            name = ent.text.strip()

    if not name:
        match = re.search(r'between\s+([A-Z][a-zA-Z\s]+?),', text)
        if match:
            name = match.group(1).strip()

    # Loan Amount
    match = re.search(r'principal sum of\s+\$[\d,]+(?:\.\d{2})?', text, re.IGNORECASE)
    if match:
        amount = match.group(0).split("of")[-1].strip()
    else:
        match = re.search(r'\$\d[\d,]*(?:\.\d{2})?', text)
        if match:
            amount = match.group(0)

    # Property Address (based on ZIP pattern or sentence stopper)
    cleaned = re.sub(r'\n+', '\n', text.strip())
    lines = cleaned.splitlines()

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

    # Final cleanup
    if address:
        # Cut at ZIP or legal phrase
        zip_match = re.search(r'\d{5}(?:-\d{4})?', address)
        if zip_match:
            address = address[:zip_match.end()]
        else:
            address = re.split(r'\bIN WITNESS\b|\bNOW THEREFORE\b', address, flags=re.IGNORECASE)[0]

        address = re.sub(r'[^\w\s.,#-]', '', address)
        address = re.sub(r',+', ',', address).strip()

    return name or "Not found", amount or "Not found", address or "Not found"

@app.post("/extract/")
async def extract(file: UploadFile = File(...)):
    ext = file.filename.split('.')[-1].lower()
    if ext not in ['jpg', 'jpeg', 'png', 'pdf']:
        raise HTTPException(status_code=400, detail="Only JPG, PNG, or PDF files are allowed")

    file_bytes = await file.read()

    if ext == 'pdf':
        images = convert_from_bytes(file_bytes)
        if not images:
            raise HTTPException(status_code=400, detail="PDF couldn't be read")
        img = np.array(images[0])
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    else:
        img = preprocess_image(file_bytes)

    text = pytesseract.image_to_string(img)

    print("\n=== OCR TEXT START ===\n", text, "\n=== OCR TEXT END ===\n")

    name, amount, address = extract_entities(text)

    cur.execute("INSERT INTO documents (borrower_name, loan_amount, property_address) VALUES (?, ?, ?)",
                (name, amount, address))
    conn.commit()

    return {
        "borrower_name": name,
        "loan_amount": amount,
        "property_address": address
    }
