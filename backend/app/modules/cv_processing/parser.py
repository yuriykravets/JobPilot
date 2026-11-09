import io
import re
from typing import Tuple
import pdfplumber


class PDFParsingError(Exception):
    """Raised when a PDF cannot be parsed or lacks readable text."""
    pass


def extract_text_from_pdf(file_bytes: bytes) -> Tuple[str, int]:
    """
    Extracts text from a digital PDF file using pdfplumber with layout awareness.
    
    Args:
        file_bytes: Raw bytes of the uploaded PDF file.
        
    Returns:
        Tuple of (extracted_text, page_count).
        
    Raises:
        PDFParsingError: If the file is not a valid PDF or contains insufficient readable text.
    """
    if not file_bytes:
        raise PDFParsingError("Uploaded file is empty.")

    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            page_count = len(pdf.pages)
            if page_count == 0:
                raise PDFParsingError("PDF file contains 0 pages.")

            extracted_pages = []
            for i, page in enumerate(pdf.pages):
                # extract_text with layout preservation
                page_text = page.extract_text(layout=True)
                if not page_text:
                    # Fallback to standard flow if layout extraction yields empty
                    page_text = page.extract_text() or ""
                
                cleaned = _normalize_whitespace(page_text)
                if cleaned:
                    extracted_pages.append(cleaned)

            full_text = "\n\n".join(extracted_pages).strip()

            # Guard against scanned/image-only PDFs
            if len(full_text) < 50:
                raise PDFParsingError(
                    "The PDF appears to be a scanned image or contains insufficient readable digital text. "
                    "Please upload a standard text-based PDF resume."
                )

            return full_text, page_count

    except PDFParsingError:
        raise
    except Exception as e:
        raise PDFParsingError(f"Failed to parse PDF document: {str(e)}") from e


def _normalize_whitespace(text: str) -> str:
    """Normalizes multiple consecutive spaces while keeping newlines intact."""
    # Replace multiple horizontal spaces/tabs with a single space
    text = re.sub(r"[ \t]+", " ", text)
    # Replace more than two consecutive newlines with two newlines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
