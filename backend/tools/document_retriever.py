"""
Document retrieval tool — wraps the pgvector retriever for use in agent tool loops.
"""
from __future__ import annotations
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


def format_retrieval_results(results: list[dict]) -> str:
    """Format retrieval results as readable text with citations."""
    if not results:
        return "No relevant documents found."
    parts = []
    for r in results:
        parts.append(
            f"[Source: {r['filename']}, chunk {r['chunk_index']} | score: {r['score']:.2f}]\n{r['content']}"
        )
    return "\n\n---\n\n".join(parts)
