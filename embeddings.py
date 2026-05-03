from __future__ import annotations
import re
import string
from collections import Counter
from typing import Tuple
from sentence_transformers import SentenceTransformer
import numpy as np

MODEL_NAME = "all-MiniLM-L6-v2"
_model_cache: dict = {}


def _get_model():
    """Load and cache the sentence-transformer model once. Returns None on failure."""
    if "model" in _model_cache:
        return _model_cache["model"]
    try:
        model = SentenceTransformer(MODEL_NAME)
        _model_cache["model"] = model
        return model
    except Exception:
        _model_cache["model"] = None
        return None


def _tfidf_cosine(text_a: str, text_b: str) -> float:
    """TF-IDF cosine similarity - fallback when model unavailable."""
    def tokenize(t: str) -> list[str]:
        t = re.sub(r"[^a-z0-9\s]", " ", t.lower())
        return t.split()

    def vec(tokens: list[str], vocab: list[str]) -> np.ndarray:
        tf = Counter(tokens)
        v = np.array([tf.get(w, 0) for w in vocab], dtype=float)
        norm = np.linalg.norm(v)
        return v / norm if norm else v

    ta, tb = tokenize(text_a), tokenize(text_b)
    vocab = list(set(ta) | set(tb))
    return float(np.dot(vec(ta, vocab), vec(tb, vocab)))


_STOPWORDS: set[str] = {
    "the", "and", "for", "with", "are", "you", "will", "have", "this",
    "that", "from", "our", "your", "their", "able", "must", "strong",
    "good", "work", "team", "role", "join", "help", "build", "using",
    "use", "well", "also", "both", "can", "experience", "skills", "years",
    "year", "looking", "preferred", "required", "plus", "etc", "including",
    "not", "but", "its", "has", "more", "than", "what", "how", "why",
    "all", "new", "job", "candidate", "position", "company",
}

_MULTI_WORD = [
    r"machine learning", r"deep learning", r"natural language processing",
    r"computer vision", r"data science", r"data engineering",
    r"software engineering", r"software development", r"web development",
    r"cloud computing", r"rest api", r"graphql", r"ci/cd", r"devops",
    r"large language model", r"llm", r"fine.tuning", r"transfer learning",
    r"neural network", r"transformer model", r"version control",
    r"object.oriented", r"test.driven", r"agile methodology",
    r"docker", r"kubernetes", r"fastapi", r"django", r"flask",
    r"react", r"node\.?js", r"postgresql", r"mongodb", r"redis",
    r"aws", r"gcp", r"azure", r"terraform",
    r"pandas", r"numpy", r"scikit.learn", r"pytorch", r"tensorflow",
]


def _tokenise_skills(text: str) -> set[str]:
    """Extract skill tokens including common multi-word tech phrases."""
    text_lower = text.lower()
    found: set[str] = set()

    for pattern in _MULTI_WORD:
        for m in re.finditer(pattern, text_lower):
            found.add(m.group())

    translator = str.maketrans("", "", string.punctuation.replace("#", "").replace("+", ""))
    clean = text_lower.translate(translator)
    tokens = {t for t in clean.split() if len(t) > 2 and t not in _STOPWORDS}
    return tokens | found


def compute_match_score(
    resume_text: str,
    jd_text: str,
    embedding_weight: float = 0.70,
    keyword_weight: float = 0.30,
) -> Tuple[float, float]:
    """
    Compute overall match score and keyword overlap score.

    Returns (overall_score_pct, skill_overlap_pct) both in [0, 100].
    """
    resume_chunk = resume_text[:4000]
    jd_chunk = jd_text[:3000]

    model = _get_model()
    if model is not None:
        embeddings = model.encode(
            [resume_chunk, jd_chunk], normalize_embeddings=True, show_progress_bar=False
        )
        cos_sim = float(np.dot(embeddings[0], embeddings[1]))
    else:
        cos_sim = _tfidf_cosine(resume_chunk, jd_chunk)

    cos_sim = max(0.0, min(1.0, cos_sim))
    embedding_score = cos_sim * 100.0

    resume_tokens = _tokenise_skills(resume_text)
    jd_tokens = _tokenise_skills(jd_text)
    if jd_tokens:
        skill_overlap_pct = min((len(resume_tokens & jd_tokens) / len(jd_tokens)) * 100, 100.0)
    else:
        skill_overlap_pct = 0.0

    overall_score = round(
        min(embedding_weight * embedding_score + keyword_weight * skill_overlap_pct, 100.0), 2
    )
    return overall_score, round(skill_overlap_pct, 2)
