from __future__ import annotations
import re


class ValidationError(Exception):
    """Raised when user input fails validation checks."""


# ── Thresholds
MIN_RESUME_WORDS = 30       
MIN_JD_WORDS = 20        
WARN_RESUME_WORDS = 80      
WARN_JD_WORDS = 40         


def validate_resume_text(text: str) -> None:

    clean = "\n".join(
        line for line in text.splitlines() if not line.startswith("[WARNING]")
    )
    clean = clean.strip()

    if not clean:
        raise ValidationError(
            "The resume appears to be empty. Please upload a valid resume PDF."
        )

    words = clean.split()
    word_count = len(words)

    if word_count < MIN_RESUME_WORDS:
        raise ValidationError(
            f"The resume is very short ({word_count} words). "
            "It may contain only a name and contact details. "
            "Please upload a full resume for meaningful analysis."
        )


def validate_job_description(text: str) -> None:

    clean = text.strip()

    if not clean:
        raise ValidationError(
            "The job description is empty. Please paste or upload a job description."
        )

    words = clean.split()
    word_count = len(words)

    if word_count < MIN_JD_WORDS:
        raise ValidationError(
            f"The job description is too short ({word_count} words). "
            "Please provide a more detailed description so the analysis is meaningful."
        )

    alpha_ratio = sum(1 for c in clean if c.isalpha()) / max(len(clean), 1)
    if alpha_ratio < 0.40:
        raise ValidationError(
            "The job description appears to contain mostly non-text characters. "
            "Please paste a valid job description."
        )
