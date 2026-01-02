# utils/extractor.py
import io
import re
from pdfminer.high_level import extract_text as extract_pdf_text
from docx import Document

def extract_text_from_pdf_bytes(pdf_bytes):
    try:
        with io.BytesIO(pdf_bytes) as f:
            text = extract_pdf_text(f)
        text = re.sub(r"\n{2,}", "\n", text)
        return text.strip()
    except Exception as e:
        raise RuntimeError(f"PDF extraction error: {e}")

def extract_text_from_docx_bytes(docx_bytes):
    try:
        with io.BytesIO(docx_bytes) as f:
            doc = Document(f)
            full = []
            for p in doc.paragraphs:
                if p.text.strip():          # ← removes empty lines
                    full.append(p.text.strip())

            text = "\n".join(full)
            text = re.sub(r"\n{2,}", "\n", text)
            return text.strip()
    
    except Exception as e:
        raise RuntimeError(f"DOCX extraction error: {e}")