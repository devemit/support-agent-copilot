from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Document
from app.schemas import DocumentCreate, DocumentResponse
from app.services.errors import AIProviderError
from app.services.ingestion import ingest_document


router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
def create_document(payload: DocumentCreate, db: Session = Depends(get_db)) -> DocumentResponse:
    # Manual text ingestion path, useful for API clients and tests.
    try:
        document = ingest_document(
            db=db,
            title=payload.title,
            source_name=payload.source_name,
            content=payload.content,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except AIProviderError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return _to_response(document)


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(file: UploadFile = File(...), db: Session = Depends(get_db)) -> DocumentResponse:
    # File upload path for simple .txt/.md knowledge-base documents.
    filename = file.filename or "uploaded-document.txt"
    if not filename.lower().endswith((".txt", ".md")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .txt and .md files are supported in the MVP.",
        )

    raw_content = await file.read()
    try:
        content = raw_content.decode("utf-8")
        document = ingest_document(
            db=db,
            title=filename.rsplit(".", 1)[0],
            source_name=filename,
            content=content,
        )
    except UnicodeDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must be UTF-8 text.",
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except AIProviderError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return _to_response(document)


@router.get("", response_model=list[DocumentResponse])
def list_documents(db: Session = Depends(get_db)) -> list[DocumentResponse]:
    # Includes chunk_count so the UI can show whether ingestion worked.
    documents = db.scalars(select(Document).order_by(Document.created_at.desc())).all()
    return [_to_response(document) for document in documents]


def _to_response(document: Document) -> DocumentResponse:
    return DocumentResponse(
        id=document.id,
        title=document.title,
        source_name=document.source_name,
        chunk_count=len(document.chunks),
        created_at=document.created_at,
    )
