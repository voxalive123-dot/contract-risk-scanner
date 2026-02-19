import pdfplumber
import docx
import os

def read_file(path: str) -> str:
    if not os.path.exists(path):
        raise FileNotFoundError("File not found.")

    ext = path.lower().split(".")[-1]

    if ext == "txt":
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    elif ext == "pdf":
        text = ""
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""
        return text

    elif ext in ["docx", "doc"]:
        doc = docx.Document(path)
        return "\n".join(p.text for p in doc.paragraphs)

    else:
        raise ValueError("Unsupported file type.")
