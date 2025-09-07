"""
Document loaders for ingestion.

Supported formats (recursive directory walk):
- .pdf      -> pdfminer.six
- .docx     -> python-docx
- .md       -> plain text (decode utf-8)
- .txt      -> plain text (decode utf-8)

Output contract:
- load_folder(path: str) -> list[dict]:
    Each item: {"text": str, "source": str}
    - `text` is normalized (collapsed whitespace, stripped)
    - `source` is a relative path string (e.g., "docs/file.pdf#p=3" if paging is used)
    - Skip items where cleaned text is too short (< 20 chars)

Design goals:
- Deterministic ordering (sorted by path) for reproducibility
- Clean whitespace consistently
- Handle decode errors gracefully (replace or skip with logging)
"""

from __future__ import annotations
from typing import List, Dict
from pathlib import Path
import re

def _clean_text(s: str) -> str:
    s = s.replace("\x00", " ")
    s = re.sub(r"\s+", " ", s, flags=re.MULTILINE).strip()
    return s

def _read_txt(p: Path) -> str:
    # Fallback decoding with errors='replace' for robustness
    return p.read_text(encoding="utf-8", errors="replace")

def _read_md(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace")

def _read_docx(p: Path) -> str:
    from docx import Document  # lazy import
    doc = Document(str(p))
    return "\n".join([para.text for para in doc.paragraphs])

def _read_pdf(p: Path) -> str:
    # Use pdfminer.six high-level API to extract text
    from pdfminer.high_level import extract_text  # lazy import
    text = extract_text(str(p)) or ""
    return text

def load_folder(path: str) -> List[Dict]:
    """
    Walk the folder recursively and load supported files.

    Parameters
    ----------
    path : str
        Root folder to walk.

    Returns
    -------
    List[Dict]
        [{"text": "...", "source": "relative/path.ext"}]
    """
    root = Path(path).resolve()
    if not root.exists() or not root.is_dir():
        return []

    out: List[Dict] = []
    exts = {".txt", ".md", ".docx", ".pdf"}

    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        if p.suffix.lower() not in exts:
            continue

        try:
            if p.suffix.lower() == ".txt":
                txt = _read_txt(p)
            elif p.suffix.lower() == ".md":
                txt = _read_md(p)
            elif p.suffix.lower() == ".docx":
                txt = _read_docx(p)
            elif p.suffix.lower() == ".pdf":
                txt = _read_pdf(p)
            else:
                continue

            cleaned = _clean_text(txt)
            if len(cleaned) < 20:
                continue

            rel = str(p.relative_to(root))
            out.append({"text": cleaned, "source": rel})
        except Exception:
            # For POC: swallow file-level errors to keep pipeline running
            continue

    return out
