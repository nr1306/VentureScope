"""
Embedding utility — uses OpenAI text-embedding-3-small.
Returns float vectors stored in pgvector.
"""
from __future__ import annotations
import asyncio

from openai import APIConnectionError, APIStatusError, APITimeoutError, AsyncOpenAI, RateLimitError
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from config import settings


def _get_client() -> AsyncOpenAI:
    return AsyncOpenAI(
        api_key=settings.openai_api_key,
        timeout=settings.openai_timeout_seconds,
        max_retries=0,
    )


class EmbeddingError(RuntimeError):
    """Raised when an embedding request fails or times out."""


def _is_retryable_embedding_error(exc: BaseException) -> bool:
    if not isinstance(exc, EmbeddingError):
        return False

    cause = exc.__cause__
    if isinstance(cause, (APIConnectionError, APITimeoutError, RateLimitError, TimeoutError)):
        return True
    if isinstance(cause, APIStatusError):
        return cause.status_code >= 500
    return cause is None


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(min=1, max=10),
    retry=retry_if_exception(_is_retryable_embedding_error),
    reraise=True,
)
async def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts. Returns list of float vectors."""
    if not texts:
        return []

    try:
        async with asyncio.timeout(settings.openai_timeout_seconds):
            response = await _get_client().embeddings.create(
                model=settings.embedding_model,
                input=texts,
                dimensions=settings.embedding_dimensions,
            )
    except TimeoutError as exc:
        raise EmbeddingError("Embedding request timed out.") from exc
    except (APIConnectionError, APITimeoutError, RateLimitError) as exc:
        raise EmbeddingError(f"Embedding request failed: {exc}") from exc
    except APIStatusError as exc:
        message = "Embedding service returned a transient server error." if exc.status_code >= 500 else "Embedding request was rejected."
        raise EmbeddingError(message) from exc

    return [item.embedding for item in response.data]


async def embed_single(text: str) -> list[float]:
    if not text.strip():
        raise EmbeddingError("Embedding input cannot be empty.")
    results = await embed_texts([text])
    return results[0]
