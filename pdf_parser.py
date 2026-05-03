import io
import re
from typing import Optional
import fitz


class PDFParseError(Exception):
    """Raised when a PDF cannot be parsed."""


def _detect_non_english(text: str) -> bool:
    """
    Heuristic check: if more than 40 % of alphabetical characters are
    outside the ASCII range (likely non-Latin script), flag as non-English.
    """
    alpha_chars = [c for c in text if c.isalpha()]
    if not alpha_chars:
        return False
    non_ascii = sum(1 for c in alpha_chars if ord(c) > 127)
    return (non_ascii / len(alpha_chars)) > 0.40


def extract_text_from_pdf(
    pdf_bytes: bytes,
    source: str = "PDF",
    max_pages: int = 60,
) -> str:

    if not pdf_bytes:
        raise PDFParseError(f"{source}: No bytes received - the file may be empty.")

    # ── Try to open the document ──────────────────────────────────────────────
    try:
        doc = fitz.open(stream=io.BytesIO(pdf_bytes), filetype="pdf")
    except fitz.FileDataError as exc:
        raise PDFParseError(
            f"{source}: Corrupted or invalid PDF file. "
            f"Please ensure the file is a valid PDF. (Detail: {exc})"
        ) from exc
    except Exception as exc:
        raise PDFParseError(f"{source}: Could not open PDF - {exc}") from exc

    # ── Encryption check ──────────────────────────────────────────────────────
    if doc.is_encrypted:
        success = doc.authenticate("")
        if not success:
            doc.close()
            raise PDFParseError(
                f"{source}: This PDF is password-protected. "
                "Please provide an unencrypted version."
            )

    total_pages = len(doc)
    pages_to_read = min(total_pages, max_pages)
    pages_skipped = total_pages - pages_to_read

    page_texts: list[str] = []
    image_only_pages = 0

    for page_num in range(pages_to_read):
        page = doc[page_num]
        text = page.get_text("text")
        text = text.strip()
        if text:
            page_texts.append(text)
        else:
            image_only_pages += 1

    doc.close()

    # ── Scanned / image-only PDF ──────────────────────────────────────────────
    if not page_texts:
        raise PDFParseError(
            f"{source}: No selectable text found. This appears to be a scanned "
            "image-only PDF. Please use a text-based PDF"
        )

    full_text = "\n\n".join(page_texts)

    # ── Non-English detection ──────────────────────────────────────────────────
    if _detect_non_english(full_text):
        raise PDFParseError(
            f"{source}: The document does not appear to be in English. "
            "This tool currently supports English-language documents only."
        )

    # ── Warnings (returned inline via special prefix that caller can strip) ───
    warnings: list[str] = []
    if image_only_pages:
        warnings.append(
            f"Note: {image_only_pages} page(s) contained only images and were skipped."
        )
    if pages_skipped:
        warnings.append(
            f"Note: Document has {total_pages} pages; only the first "
            f"{pages_to_read} were processed."
        )

    # Clean up excessive whitespace
    full_text = re.sub(r"\n{3,}", "\n\n", full_text)
    full_text = re.sub(r" {2,}", " ", full_text)

    # Prepend any warnings so the caller / UI can surface them
    if warnings:
        warning_block = "\n".join(f"[WARNING] {w}" for w in warnings)
        full_text = warning_block + "\n\n" + full_text

    return full_text
