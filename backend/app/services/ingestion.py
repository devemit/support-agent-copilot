from sqlalchemy.orm import Session

from app.models import Document, DocumentChunk
from app.services.chunking import chunk_text
from app.services.embeddings import embed_text


def ingest_document(db: Session, title: str, source_name: str | None, content: str) -> Document:
    # Ingestion turns raw support text into searchable vector-backed chunks.
    chunks = chunk_text(content)
    if not chunks:
        raise ValueError("Document did not contain any ingestible text.")

    document = Document(title=title, source_name=source_name)
    db.add(document)
    # Flush gives us document.id before committing, so chunks can reference it.
    db.flush()

    for index, chunk in enumerate(chunks):
        db.add(
            DocumentChunk(
                document_id=document.id,
                chunk_index=index,
                content=chunk,
                embedding=embed_text(chunk),
            )
        )

    db.commit()
    db.refresh(document)
    return document
