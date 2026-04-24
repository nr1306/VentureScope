"""
Tavily web search tool — used by all sub-agents.
Returns a list of {title, url, content} results.
"""
from __future__ import annotations
import asyncio

from tavily import TavilyClient

from config import settings

_client = TavilyClient(api_key=settings.tavily_api_key)

# OpenAI function tool schema
WEB_SEARCH_TOOL = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": (
            "Search the web for up-to-date information about a company, market, or topic. "
            "Always include the source URL in citations. Use specific queries for best results."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query. Be specific (e.g. 'Stripe revenue 2024 funding history').",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Number of results to return (1-10). Default 5.",
                    "default": 5,
                },
            },
            "required": ["query"],
        },
    },
}


class WebSearchError(RuntimeError):
    """Raised when Tavily search fails or times out."""


def _search_sync(query: str, max_results: int) -> dict:
    return _client.search(
        query=query,
        max_results=max_results,
        include_raw_content=False,
        include_answer=True,
    )


async def run_web_search(query: str, max_results: int = 5) -> list[dict]:
    """Execute a Tavily search. Returns list of result dicts."""
    normalized_query = query.strip()
    if not normalized_query:
        raise WebSearchError("Search query cannot be empty.")

    bounded_results = max(1, min(int(max_results or 5), 10))

    try:
        async with asyncio.timeout(settings.tavily_timeout_seconds):
            response = await asyncio.to_thread(_search_sync, normalized_query, bounded_results)
    except TimeoutError as exc:
        raise WebSearchError("Tavily search timed out.") from exc
    except Exception as exc:
        raise WebSearchError(f"Tavily search failed: {exc}") from exc

    results = []
    if response.get("answer"):
        results.append({"title": "Summary", "url": "", "content": response["answer"]})
    for r in response.get("results", []):
        results.append({
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "content": r.get("content", "")[:1000],
        })
    return results
