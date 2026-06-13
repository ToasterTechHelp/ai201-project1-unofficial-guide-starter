"""Milestone 3 — Document ingestion and chunking.

Loads every PDF in documents/, extracts and cleans the text with pdfplumber,
splits each document into ~600-character chunks with ~100-character overlap
(the strategy specified in planning.md), and writes the result to chunks.json
with source metadata for the embedding stage (Milestone 4).

Run:  python ingest.py
"""

import json
import re
from pathlib import Path

import pdfplumber

DOCUMENTS_DIR = Path("documents")
OUTPUT_FILE = Path("chunks.json")

CHUNK_SIZE = 600     # characters — see planning.md "Chunking Strategy"
OVERLAP = 100        # characters of overlap between adjacent chunks

# Boilerplate lines that appear on tax forms but carry no answerable content.
# Matched case-insensitively against individual (stripped) lines.
BOILERPLATE_PATTERNS = [
    r"^cat\.?\s*no\.",                       # "Cat. No. 11320B"
    r"^www\.irs\.gov",                       # IRS URLs
    r"for paperwork reduction act notice",   # standard footer
    r"^omb no\.",                            # "OMB No. 1545-0074"
    r"^page\s+\d+\s*$",                       # bare page numbers
    r"^\(?rev\.",                            # "(Rev. December 2023)"
]
_BOILERPLATE_RE = re.compile("|".join(BOILERPLATE_PATTERNS), re.IGNORECASE)


def load_pdf(path: Path) -> str:
    """Extract raw text from a PDF. Returns '' for image-only/scanned PDFs."""
    pages = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                pages.append(text)
    return "\n\n".join(pages)


def clean_text(text: str) -> str:
    """Remove form boilerplate and normalize whitespace.

    Conservative on purpose: it drops only lines that match a known
    boilerplate pattern, then collapses runs of blank lines and spaces so
    chunking isn't thrown off by the ragged spacing pdfplumber produces.
    """
    kept_lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if _BOILERPLATE_RE.search(stripped):
            continue
        # form line-items are padded with dotted leaders (". . . . .") that
        # carry no meaning — collapse any run of 3+ dots/spaces to one space
        stripped = re.sub(r"(?:\s*\.\s*){3,}", " ", stripped)
        # pdfplumber emits U+FFFD for some glyphs; the common case is the
        # possessive apostrophe ("Preparer�s" -> "Preparer's")
        stripped = stripped.replace("�s", "'s").replace("�", " ")
        # collapse internal runs of whitespace within a line
        stripped = re.sub(r"\s{2,}", " ", stripped).strip()
        if stripped:
            kept_lines.append(stripped)
    return "\n".join(kept_lines)


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = OVERLAP) -> list[str]:
    """Split text into ~chunk_size character windows with `overlap` carry-over.

    Windows are nudged to the nearest preceding whitespace so chunks don't end
    mid-word, which keeps a line's label and its value from being split apart.
    """
    text = text.strip()
    if not text:
        return []

    chunks = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + chunk_size, n)
        # back off to a word boundary if we're not at the very end
        if end < n:
            boundary = text.rfind(" ", start, end)
            if boundary > start:
                end = boundary
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= n:
            break
        start = end - overlap  # step forward, keeping `overlap` chars of context
    return chunks


def main() -> None:
    pdf_paths = sorted(DOCUMENTS_DIR.glob("*.pdf"))
    if not pdf_paths:
        raise SystemExit(f"No PDFs found in {DOCUMENTS_DIR}/")

    all_chunks = []
    per_doc_counts = {}

    for path in pdf_paths:
        raw = load_pdf(path)
        if not raw.strip():
            print(f"⚠  {path.name}: no extractable text (scanned/image-only?) — skipped")
            continue
        cleaned = clean_text(raw)
        doc_chunks = chunk_text(cleaned)
        per_doc_counts[path.name] = len(doc_chunks)
        for i, chunk in enumerate(doc_chunks):
            all_chunks.append({
                "id": f"{path.stem}-{i}",
                "source": path.name,
                "chunk_index": i,
                "text": chunk,
            })

    OUTPUT_FILE.write_text(json.dumps(all_chunks, indent=2), encoding="utf-8")

    # ---- Inspection output (Milestone 3 checkpoint) ----
    print("\nChunks per document:")
    for name, count in per_doc_counts.items():
        print(f"  {name:18s} {count:4d} chunks")
    print(f"\nTotal chunks across {len(per_doc_counts)} documents: {len(all_chunks)}")
    print(f"Wrote {OUTPUT_FILE}")

    print("\n--- 5 representative chunks (inspect for completeness/cleanliness) ---")
    sample_idxs = [int(i * (len(all_chunks) - 1) / 4) for i in range(5)] if len(all_chunks) >= 5 else range(len(all_chunks))
    for idx in sample_idxs:
        c = all_chunks[idx]
        print(f"\n[{c['id']}] (source: {c['source']}, {len(c['text'])} chars)")
        print(c["text"])


if __name__ == "__main__":
    main()
