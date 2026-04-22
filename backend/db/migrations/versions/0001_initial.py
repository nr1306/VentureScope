"""Initial schema with pgvector

Revision ID: 0001
Revises:
Create Date: 2026-04-11
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "reports",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("company_name", sa.String(255), nullable=False),
        sa.Column("status", sa.String(50), server_default="pending"),
        sa.Column("celery_task_id", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("result", sa.JSON, nullable=True),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("langfuse_trace_id", sa.String(255), nullable=True),
    )
    op.create_index("ix_reports_company_name", "reports", ["company_name"])

    op.create_table(
        "report_sections",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("report_id", sa.String(36), sa.ForeignKey("reports.id", ondelete="CASCADE"), nullable=False),
        sa.Column("section", sa.String(50), nullable=False),
        sa.Column("summary", sa.Text, nullable=False),
        sa.Column("key_findings", sa.JSON, nullable=False),
        sa.Column("risk_level", sa.String(20), nullable=False),
        sa.Column("confidence", sa.Float, nullable=False),
        sa.Column("citations", sa.JSON, nullable=False),
        sa.Column("llm_judge_score", sa.Float, nullable=True),
        sa.Column("guardrails_triggered", sa.JSON, server_default="[]"),
        sa.Column("agent_steps", sa.JSON, server_default="[]"),
    )
    op.create_index("ix_report_sections_report_id", "report_sections", ["report_id"])

    op.create_table(
        "documents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("company_name", sa.String(255), nullable=False),
        sa.Column("filename", sa.String(500), nullable=False),
        sa.Column("content_type", sa.String(100), nullable=False),
        sa.Column("chunk_count", sa.Integer, server_default="0"),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_documents_company_name", "documents", ["company_name"])

    op.create_table(
        "document_chunks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("document_id", sa.String(36), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("company_name", sa.String(255), nullable=False),
        sa.Column("chunk_index", sa.Integer, nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("embedding", Vector(1536), nullable=False),
        sa.Column("metadata", sa.JSON, server_default="{}"),
    )
    op.create_index("ix_document_chunks_document_id", "document_chunks", ["document_id"])
    op.create_index("ix_document_chunks_company_name", "document_chunks", ["company_name"])
    # IVFFlat index for ANN search (created after data load in practice)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_document_chunks_embedding "
        "ON document_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
    )

    op.create_table(
        "eval_results",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("run_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("company_name", sa.String(255), nullable=False),
        sa.Column("report_id", sa.String(255), nullable=True),
        sa.Column("scores", sa.JSON, nullable=False),
        sa.Column("judge_feedback", sa.JSON, server_default="{}"),
    )


def downgrade() -> None:
    op.drop_table("eval_results")
    op.drop_table("document_chunks")
    op.drop_table("documents")
    op.drop_table("report_sections")
    op.drop_table("reports")
