"""
pgvector similarity retriever.
Converts a query to an embedding then fetches the top-k closest chunks.
"""
from __future__ import annotations

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from db.models import DocumentChunk
from rag.embedder import embed_single


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
    top_k = top_k or settings.retrieval_top_k
    query_embedding = await embed_single(query)

    # pgvector cosine distance: <=> operator (lower = more similar)
    stmt = (
        select(
            DocumentChunk.id,
            DocumentChunk.content,
            DocumentChunk.metadata_,
            (1 - DocumentChunk.embedding.cosine_distance(query_embedding)).label("score"),
        )
        .where(DocumentChunk.company_name == company_name)
        .order_by(DocumentChunk.embedding.cosine_distance(query_embedding))
        .limit(top_k)
    )

    result = await db.execute(stmt)
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
