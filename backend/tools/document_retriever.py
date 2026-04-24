"""
Document retrieval tool — wraps the pgvector retriever for use in agent tool loops.
"""
from __future__ import annotations
from collections.abc import Awaitable, Callable
from typing import Any

DOCUMENT_RETRIEVER_TOOL = {
    "type": "function",
    "function": {
        "name": "document_retriever",
        "description": (
            "Search uploaded documents (pitch decks, financials, reports) for a specific company. "
            "Use this to find proprietary information not available on the web. "
            "Always cite the source document and chunk in citations."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "What to look for in the documents.",
                },
                "top_k": {
                    "type": "integer",
                    "description": "Number of chunks to retrieve (1-10). Default 5.",
                    "default": 5,
                },
            },
            "required": ["query"],
        },
    },
}


async def run_document_retriever(
    rag_retrieve: Callable[..., Awaitable[list[dict[str, Any]]]] | None,
    query: str,
    top_k: int = 5,
) -> str:
    if rag_retrieve is None:
        raise RuntimeError("Document retriever is unavailable for this run.")

    normalized_query = query.strip()
    if not normalized_query:
        raise ValueError("Document retrieval query cannot be empty.")

    bounded_top_k = max(1, min(int(top_k or 5), 10))
    results = await rag_retrieve(query=normalized_query, top_k=bounded_top_k)
    return format_retrieval_results(results)


def format_retrieval_results(results: list[dict]) -> str:
    """Format retrieval results as readable text with citations."""
    if not results:
        return "No relevant documents found."
    parts = []
    for r in results:
        parts.append(
            f"[Source: {r.get('filename', 'unknown')}, chunk {r.get('chunk_index', 0)} | score: {float(r.get('score', 0.0)):.2f}]\n{r.get('content', '')}"
        )
    return "\n\n---\n\n".join(parts)
