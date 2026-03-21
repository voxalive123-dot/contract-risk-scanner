from dataclasses import dataclass

import pytesseract
from pdf2image import convert_from_path
from pypdf import PdfReader


MAX_PDF_PAGES = 100
OCR_DPI = 200

EXTRACTION_METHOD_NATIVE = "native"
EXTRACTION_METHOD_OCR = "ocr"


@dataclass
class PdfExtractionResult:
    text: str
    page_count: int
    has_extractable_text: bool
    is_encrypted: bool
    extraction_method: str
    confidence_hint: float


class PdfExtractionError(Exception):
    pass


def _extract_text_with_ocr(file_path: str, page_count: int) -> str:
    try:
        images = convert_from_path(file_path, dpi=OCR_DPI, first_page=1, last_page=page_count)
    except Exception as exc:
        raise PdfExtractionError("PDF OCR image conversion failed") from exc

    ocr_chunks = []

    try:
        for image in images:
            ocr_text = pytesseract.image_to_string(image)
            if ocr_text and ocr_text.strip():
                ocr_chunks.append(ocr_text.strip())
    except Exception as exc:
        raise PdfExtractionError("PDF OCR text extraction failed") from exc

    return "\n".join(ocr_chunks).strip()


def extract_text_from_pdf(file_path: str) -> PdfExtractionResult:
    """
    Extract text from a PDF file and return structured extraction metadata.

    Strategy:
    1. Try normal text extraction with pypdf.
    2. If no extractable text is found, fall back to OCR.
    3. Raise PdfExtractionError for unreadable/encrypted/pathological files.
    """
    try:
        reader = PdfReader(file_path)
    except Exception as exc:
        raise PdfExtractionError("PDF could not be opened or parsed") from exc

    if reader.is_encrypted:
        raise PdfExtractionError("Encrypted PDFs are not supported")

    page_count = len(reader.pages)

    if page_count > MAX_PDF_PAGES:
        raise PdfExtractionError("PDF exceeds maximum allowed page count")

    text_chunks = []

    try:
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text and page_text.strip():
                text_chunks.append(page_text.strip())
    except Exception as exc:
        raise PdfExtractionError("PDF text extraction failed") from exc

    text = "\n".join(text_chunks).strip()

    if text:
        return PdfExtractionResult(
            text=text,
            page_count=page_count,
            has_extractable_text=True,
            is_encrypted=False,
            extraction_method=EXTRACTION_METHOD_NATIVE,
            confidence_hint=1.0,
        )

    text = _extract_text_with_ocr(file_path, page_count)

    return PdfExtractionResult(
        text=text,
        page_count=page_count,
        has_extractable_text=bool(text),
        is_encrypted=False,
        extraction_method=EXTRACTION_METHOD_OCR,
        confidence_hint=0.65 if text else 0.0,
    )
