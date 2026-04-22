"""
Document ingestion pipeline:
  raw bytes → parse text → chunk → embed → store in pgvector
"""
from __future__ import annotations
import io
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from db.models import Document, DocumentChunk
from rag.chunker import split_text
from rag.embedder import embed_texts


SUPPORTED_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
    "text/markdown",
}


def _parse_document(filename: str, content_type: str, contents: bytes) -> str:
    """Extract plain text from uploaded file."""
    if content_type == "application/pdf" or filename.lower().endswith(".pdf"):
        import pypdf
        reader = pypdf.PdfReader(io.BytesIO(contents))
        return "\n\n".join(
            page.extract_text() or "" for page in reader.pages
        ).strip()

    if (
        content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        or filename.lower().endswith(".docx")
    ):
        import docx
        doc = docx.Document(io.BytesIO(contents))
        return "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())

    # Plain text / markdown
    return contents.decode("utf-8", errors="replace")


async def ingest_document(
    db: AsyncSession,
    company_name: str,
    filename: str,
    content_type: str,
    contents: bytes,
) -> tuple[str, int]:
    """
    Parse, chunk, embed, and store a document.
    Returns (document_id, chunk_count).
    """
    text = _parse_document(filename, content_type, contents)
    chunks = split_text(text)

    if len(chunks) > settings.max_chunks_per_doc:
        chunks = chunks[:settings.max_chunks_per_doc]

    doc_id = str(uuid.uuid4())
    doc = Document(
        id=doc_id,
        company_name=company_name,
        filename=filename,
        content_type=content_type,
        chunk_count=len(chunks),
    )
    db.add(doc)
    await db.flush()

    # Embed in batches of 100
    batch_size = 100
    all_chunk_objs = []
    for batch_start in range(0, len(chunks), batch_size):
        batch = chunks[batch_start: batch_start + batch_size]
        embeddings = await embed_texts(batch)
        for i, (chunk_text, embedding) in enumerate(zip(batch, embeddings)):
            all_chunk_objs.append(
                DocumentChunk(
                    id=str(uuid.uuid4()),
                    document_id=doc_id,
                    company_name=company_name,
                    chunk_index=batch_start + i,
                    content=chunk_text,
                    embedding=embedding,
                    metadata_={"filename": filename, "chunk_index": batch_start + i},
                )
            )

    db.add_all(all_chunk_objs)
    await db.commit()
    return doc_id, len(chunks)
