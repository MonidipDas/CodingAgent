"""Knowledge and context management layer for the coding agent.
Provides retrieval of relevant code chunks using TF-IDF similarity, mirroring the
original `retrieve` function from `agent.py`.
"""
import os
from pathlib import Path
from typing import List

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

def retrieve(root: Path, query: str) -> str:
    """Return the most relevant code chunks for a given query.

    The function walks the workspace, indexes supported text files, and selects
    the top‑5 chunks based on cosine similarity of TF‑IDF character n‑grams.
    """
    chunks: List[str] = []
    for path in root.rglob("*"):
        # Skip hidden files, common junk directories, and unsupported extensions.
        if any(p.startswith(".") or p in {"node_modules", "venv", "__pycache__"} for p in path.relative_to(root).parts):
            continue
        if path.is_symlink() or not path.is_file() or path.suffix not in {".py", ".md", ".toml", ".txt", ".js", ".ts"}:
            continue
        if path.stat().st_size > 100_000:
            continue
        lines = path.read_text(errors="replace").splitlines()
        for start in range(0, len(lines), 60):
            chunk = f"{path.relative_to(root)}:{start + 1}\n" + "\n".join(lines[start:start + 80])
            chunks.append(chunk)
        if len(chunks) >= 2000:
            break
    if not chunks:
        return "Repository has no indexed source files."
    vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), max_features=30000)
    matrix = vectorizer.fit_transform(chunks)
    scores = cosine_similarity(vectorizer.transform([query]), matrix)[0]
    # Return top‑5 chunks, joined with double newlines.
    top_chunks = "\n\n".join(chunks[i] for i in scores.argsort()[-5:][::-1])
    return top_chunks[:16000]
