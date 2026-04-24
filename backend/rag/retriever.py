"""
pgvector similarity retriever.
Converts a query to an embedding then fetches the top-k closest chunks.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from db.models import DocumentChunk
from db.session import execute_with_retry
from rag.embedder import EmbeddingError, embed_single


class RetrievalError(RuntimeError):
    """Raised when document retrieval fails."""


async def retrieve(
    db: AsyncSession,
    company_name: str,
    query: str,
    top_k: int | None = None,
) -> list[dict]:
    """
    Return top_k chunks most similar to query for the given company namespace.
    Each result: {"chunk_id", "content", "score", "filename", "chunk_index"}
    """
    normalized_company = company_name.strip()
    normalized_query = query.strip()
    if not normalized_company:
        return []
    if not normalized_query:
        raise RetrievalError("Retrieval query cannot be empty.")

    top_k = max(1, min(top_k or settings.retrieval_top_k, 20))

    try:
        query_embedding = await embed_single(normalized_query)
    except EmbeddingError as exc:
        raise RetrievalError(f"Failed to embed retrieval query: {exc}") from exc

    # pgvector cosine distance: <=> operator (lower = more similar)
    stmt = (
        select(
            DocumentChunk.id,
            DocumentChunk.content,
            DocumentChunk.metadata_,
            (1 - DocumentChunk.embedding.cosine_distance(query_embedding)).label("score"),
        )
        .where(DocumentChunk.company_name == normalized_company)
        .order_by(DocumentChunk.embedding.cosine_distance(query_embedding))
        .limit(top_k)
    )

    try:
        result = await execute_with_retry(db, stmt)
    except Exception as exc:
        raise RetrievalError(f"Document retrieval query failed: {exc}") from exc

    rows = result.all()
    return [
        {
            "chunk_id": row.id,
            "content": row.content,
            "score": float(row.score),
            "filename": row.metadata_.get("filename", "unknown"),
            "chunk_index": row.metadata_.get("chunk_index", 0),
        }
        for row in rows
    ]
