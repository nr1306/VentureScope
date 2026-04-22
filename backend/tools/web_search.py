"""
Tavily web search tool — used by all sub-agents.
Returns a list of {title, url, content} results.
"""
from __future__ import annotations
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


def run_web_search(query: str, max_results: int = 5) -> list[dict]:
    """Execute a Tavily search. Returns list of result dicts."""
    response = _client.search(
        query=query,
        max_results=max_results,
        include_raw_content=False,
        include_answer=True,
    )
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
