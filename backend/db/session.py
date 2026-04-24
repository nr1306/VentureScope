from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TypeVar

from fastapi import HTTPException
from sqlalchemy.exc import DBAPIError, InterfaceError, OperationalError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool
from tenacity import AsyncRetrying, retry_if_exception, stop_after_attempt, wait_exponential

from config import settings

# NullPool prevents asyncpg connections from being cached across event loop
# invocations (required for Celery fork workers where asyncio.run() creates
# a fresh loop per task).
engine = create_async_engine(
    settings.database_url,
    echo=False,
    poolclass=NullPool,
    pool_pre_ping=True,
    connect_args={
        "timeout": settings.db_connect_timeout_seconds,
        "command_timeout": settings.db_statement_timeout_seconds,
    },
)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
T = TypeVar("T")


class Base(DeclarativeBase):
    pass


def is_transient_db_error(exc: BaseException) -> bool:
    if isinstance(exc, (OperationalError, InterfaceError)):
        return True
    if isinstance(exc, DBAPIError) and getattr(exc, "connection_invalidated", False):
        return True

    message = str(getattr(exc, "orig", exc)).lower()
    transient_signals = (
        "connection refused",
        "connection reset",
        "connection timed out",
        "could not connect",
        "deadlock detected",
        "server closed the connection unexpectedly",
        "temporarily unavailable",
        "timeout",
        "too many connections",
        "try again",
    )
    return any(signal in message for signal in transient_signals)


def _db_retrying() -> AsyncRetrying:
    return AsyncRetrying(
        reraise=True,
        stop=stop_after_attempt(settings.db_retry_attempts),
        wait=wait_exponential(
            multiplier=settings.db_retry_backoff_seconds,
            min=settings.db_retry_backoff_seconds,
            max=max(settings.db_retry_backoff_seconds * 4, settings.db_retry_backoff_seconds),
        ),
        retry=retry_if_exception(is_transient_db_error),
    )


async def run_with_db_retry(operation: Callable[[], Awaitable[T]]) -> T:
    async for attempt in _db_retrying():
        with attempt:
            return await operation()
    raise RuntimeError("DB retry loop exited unexpectedly")


async def execute_with_retry(session: AsyncSession, *args, **kwargs):
    async def _execute():
        try:
            return await session.execute(*args, **kwargs)
        except Exception:
            await session.rollback()
            raise

    return await run_with_db_retry(_execute)


async def flush_with_retry(session: AsyncSession) -> None:
    async def _flush() -> None:
        try:
            await session.flush()
        except Exception:
            await session.rollback()
            raise

    await run_with_db_retry(_flush)


async def commit_with_retry(session: AsyncSession) -> None:
    async def _commit() -> None:
        try:
            await session.commit()
        except Exception:
            await session.rollback()
            raise

    await run_with_db_retry(_commit)


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except SQLAlchemyError as exc:
            await session.rollback()
            status_code = 503 if is_transient_db_error(exc) else 500
            detail = "Database temporarily unavailable." if status_code == 503 else "Database request failed."
            raise HTTPException(status_code=status_code, detail=detail) from exc
