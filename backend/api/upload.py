from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db
from db.models import Document
from guardrails.input_guardrails import validate_upload
from rag.ingestor import ingest_document

router = APIRouter(tags=["upload"])


@router.post("/upload")
async def upload_document(
    company_name: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    contents = await file.read()

    # Input guardrail — validates size, content type
    validate_upload(filename=file.filename, content_type=file.content_type, size_bytes=len(contents))

    doc_id, chunk_count = await ingest_document(
        db=db,
        company_name=company_name,
        filename=file.filename,
        content_type=file.content_type,
        contents=contents,
    )

    return {
        "document_id": doc_id,
        "company_name": company_name,
        "filename": file.filename,
        "chunk_count": chunk_count,
        "message": f"Successfully ingested {chunk_count} chunks.",
    }


@router.get("/documents/{company_name}")
async def list_documents(company_name: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).where(Document.company_name == company_name))
    docs = result.scalars().all()
    return [
        {
            "id": d.id,
            "filename": d.filename,
            "chunk_count": d.chunk_count,
            "uploaded_at": d.uploaded_at,
        }
        for d in docs
    ]
