from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from db.session import engine, Base
from api import analyze, reports, upload, evals


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Settings are validated at import time; accessing them here makes startup
    # fail fast before serving traffic if a critical environment variable is missing.
    settings.model_dump()

    # Tables are managed by Alembic; this is a fallback for local dev
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        yield
    finally:
        await engine.dispose()


app = FastAPI(
    title="VentureScope API",
    description="Multi-agent investment due diligence system",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://frontend:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analyze.router, prefix="/api")
app.include_router(reports.router, prefix="/api")
app.include_router(upload.router, prefix="/api")
app.include_router(evals.router, prefix="/api")


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "venturesscope"}
