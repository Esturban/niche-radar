from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader


def load_resume(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".md", ".txt"}:
        text = path.read_text(encoding="utf-8")
    elif suffix == ".pdf":
        reader = PdfReader(str(path))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    else:
        raise ValueError(f"Unsupported resume format: {suffix}")

    normalized = normalize_text(text)
    if not normalized.strip():
        raise ValueError("Resume/profile contained no extractable text.")
    return normalized


def normalize_text(text: str) -> str:
    return "\n".join(line.strip() for line in text.replace("\r\n", "\n").splitlines() if line.strip())

