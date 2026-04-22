"""
Simple recursive character text splitter.
Avoids depending on LangChain — implements the same logic directly.
"""
from __future__ import annotations
from config import settings


def split_text(text: str, chunk_size: int | None = None, overlap: int | None = None) -> list[str]:
    chunk_size = chunk_size or settings.chunk_size
    overlap = overlap or settings.chunk_overlap

    separators = ["\n\n", "\n", ". ", " ", ""]
    return _split_recursive(text, separators, chunk_size, overlap)


def _split_recursive(text: str, separators: list[str], chunk_size: int, overlap: int) -> list[str]:
    if len(text) <= chunk_size:
        return [text.strip()] if text.strip() else []

    separator = ""
    for sep in separators:
        if sep in text:
            separator = sep
            break

    parts = text.split(separator) if separator else list(text)
    chunks: list[str] = []
    current = ""

    for part in parts:
        candidate = current + separator + part if current else part
        if len(candidate) <= chunk_size:
            current = candidate
        else:
            if current:
                chunks.append(current.strip())
            if len(part) > chunk_size:
                # Recurse with next separator
                sub = _split_recursive(part, separators[1:], chunk_size, overlap)
                chunks.extend(sub)
                current = sub[-1] if sub else ""
            else:
                current = part

    if current.strip():
        chunks.append(current.strip())

    # Apply overlap: prepend tail of previous chunk to next
    if overlap > 0 and len(chunks) > 1:
        overlapped = [chunks[0]]
        for i in range(1, len(chunks)):
            tail = chunks[i - 1][-overlap:]
            overlapped.append(tail + " " + chunks[i])
        return overlapped

    return chunks
