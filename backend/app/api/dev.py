from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Document, DocumentChunk
from app.services.embeddings import embed_text
from app.services.errors import AIProviderError
from app.services.ingestion import ingest_document


router = APIRouter(prefix="/dev", tags=["dev"])


@router.post("/seed-sample-data")
def seed_sample_data(db: Session = Depends(get_db)) -> dict[str, int]:
    # Development-only helper so the MVP has a knowledge base in one API call.
    sample_dir = Path("/app/sample_docs")
    if not sample_dir.exists():
        sample_dir = Path(__file__).resolve().parents[2] / "sample_docs"

    created = 0
    skipped = 0
    for path in sorted(sample_dir.glob("*.md")):
        exists = db.scalar(select(Document.id).where(Document.source_name == path.name))
        if exists:
            skipped += 1
            continue

        content = path.read_text(encoding="utf-8")
        try:
            ingest_document(
                db=db,
                title=path.stem.replace("-", " ").title(),
                source_name=path.name,
                content=content,
            )
        except AIProviderError as exc:
            db.rollback()
            raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
        created += 1

    return {"documents_created": created, "documents_skipped": skipped}


@router.post("/reindex-documents")
def reindex_documents(db: Session = Depends(get_db)) -> dict[str, int]:
    # Recompute embeddings after changing AI_PROVIDER or embedding model.
    chunks = db.scalars(select(DocumentChunk)).all()
    try:
        for chunk in chunks:
            chunk.embedding = embed_text(chunk.content)
    except AIProviderError as exc:
        db.rollback()
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    db.commit()
    return {"chunks_reindexed": len(chunks)}
