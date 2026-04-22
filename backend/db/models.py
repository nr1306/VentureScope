import uuid
from datetime import datetime, timezone
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    String, Text, Float, Integer, DateTime, JSON, ForeignKey, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from config import settings
from db.session import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    company_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), default="pending")  # pending | running | completed | failed
    celery_task_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Full structured report (JSON)
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Langfuse trace ID for deep-linking
    langfuse_trace_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    sections = relationship("ReportSection", back_populates="report", cascade="all, delete-orphan")


class ReportSection(Base):
    __tablename__ = "report_sections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    report_id: Mapped[str] = mapped_column(ForeignKey("reports.id", ondelete="CASCADE"), index=True)
    section: Mapped[str] = mapped_column(String(50))  # market|financial|competitor|risk
    summary: Mapped[str] = mapped_column(Text)
    key_findings: Mapped[list] = mapped_column(JSON)
    risk_level: Mapped[str] = mapped_column(String(20))
    confidence: Mapped[float] = mapped_column(Float)
    citations: Mapped[list] = mapped_column(JSON)
    llm_judge_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    guardrails_triggered: Mapped[list] = mapped_column(JSON, default=list)
    agent_steps: Mapped[list] = mapped_column(JSON, default=list)

    report = relationship("Report", back_populates="sections")


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    company_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    filename: Mapped[str] = mapped_column(String(500))
    content_type: Mapped[str] = mapped_column(String(100))
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    company_name: Mapped[str] = mapped_column(String(255), index=True)
    chunk_index: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[Any] = mapped_column(Vector(settings.embedding_dimensions))
    metadata_: Mapped[dict] = mapped_column("metadata", JSON, default=dict)

    document = relationship("Document", back_populates="chunks")

    __table_args__ = (
        Index(
            "ix_document_chunks_embedding",
            "embedding",
            postgresql_using="ivfflat",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )


class EvalResult(Base):
    __tablename__ = "eval_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    company_name: Mapped[str] = mapped_column(String(255))
    report_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    scores: Mapped[dict] = mapped_column(JSON)
    judge_feedback: Mapped[dict] = mapped_column(JSON, default=dict)
