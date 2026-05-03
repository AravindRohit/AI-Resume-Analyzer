from __future__ import annotations
import re
import unicodedata


def sanitize_text(text: str) -> str:
    if not text:
        return ""
    text = unicodedata.normalize("NFC", text)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


def truncate_text(text: str, max_chars: int = 2000) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "\n\n… [truncated for preview]"


def word_count(text: str) -> int:
    return len(text.split())


def extract_warning_lines(text: str) -> tuple[list[str], str]:
    lines = text.splitlines()
    warnings = [
        line.replace("[WARNING] ", "").strip()
        for line in lines
        if line.startswith("[WARNING]")
    ]
    clean = "\n".join(
        line for line in lines if not line.startswith("[WARNING]")
    ).strip()
    return warnings, clean
