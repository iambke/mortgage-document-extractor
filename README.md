# Mortgage Document Extractor

A web application that extracts key information from mortgage documents (PDFs or images) using OCR, NLP, and FastAPI.

## Features

- Upload mortgage documents (PDF/JPG/PNG)
- Extracts borrower name, loan amount, and property address
- Uses Tesseract OCR, spaCy NLP, and OpenCV for preprocessing
- Stores results in SQLite
- Includes a simple HTML/CSS/JavaScript frontend

## Tech Stack

- Backend: FastAPI, pytesseract, spaCy, OpenCV
- Frontend: HTML, CSS, JavaScript
- Database: SQLite

## Setup

1. Clone the repository  
   `git clone https://github.com/iambke/mortgage-document-extractor.git`

2. Install dependencies  
   `pip install -r requirements.txt`  
   `python -m spacy download en_core_web_sm`

3. Install Tesseract OCR:  
   [https://github.com/tesseract-ocr/tesseract](https://github.com/tesseract-ocr/tesseract)

4. Start the application  
   `uvicorn backend:app --reload`

5. Visit  
   `http://127.0.0.1:8000/`

## Project Structure

```
mortgage-document-exractor/
├── backend.py
├── requirements.txt               
└── static/
    ├── index.html         
    ├── style.css      
    ├── script.js   

````

## Notes

This project validates document content to ensure mortgage relevance before extracting and storing information.
