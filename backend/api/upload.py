from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db
from db.models import Document
from db.session import execute_with_retry
from guardrails.input_guardrails import validate_company_input, validate_upload
from rag.ingestor import DocumentIngestionError, ingest_document

router = APIRouter(tags=["upload"])


@router.post("/upload")
async def upload_document(
    company_name: Annotated[str, Form(min_length=1, max_length=200)],
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    safe_company_name = company_name.strip()
    validate_company_input(safe_company_name)

    try:
        contents = await file.read()
        safe_filename = validate_upload(
            filename=file.filename,
            content_type=file.content_type,
            size_bytes=len(contents),
            contents=contents,
        )

        doc_id, chunk_count = await ingest_document(
            db=db,
            company_name=safe_company_name,
            filename=safe_filename,
            content_type=file.content_type or "application/octet-stream",
            contents=contents,
        )
    except DocumentIngestionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Document ingestion failed.") from exc
    finally:
        await file.close()

    return {
        "document_id": doc_id,
        "company_name": safe_company_name,
        "filename": safe_filename,
        "chunk_count": chunk_count,
        "message": f"Successfully ingested {chunk_count} chunks.",
    }


@router.get("/documents/{company_name}")
async def list_documents(company_name: str, db: AsyncSession = Depends(get_db)):
    safe_company_name = company_name.strip()
    validate_company_input(safe_company_name)
    result = await execute_with_retry(db, select(Document).where(Document.company_name == safe_company_name))
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
