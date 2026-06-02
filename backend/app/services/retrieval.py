from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.config import get_settings
from app.models import DocumentChunk
from app.services.embeddings import embed_text


settings = get_settings()


@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id: int
    document_id: int
    title: str
    source_name: str | None
    content: str
    score: float


def retrieve_relevant_chunks(db: Session, query: str, top_k: int | None = None) -> list[RetrievedChunk]:
    # Embed the incoming ticket text in the same vector space as document chunks.
    query_embedding = embed_text(query)
    limit = top_k or settings.retrieval_top_k
    # Lower cosine distance means more similar. pgvector executes this in PostgreSQL.
    distance = DocumentChunk.embedding.cosine_distance(query_embedding)

    rows = db.execute(
        select(DocumentChunk, distance.label("distance"))
        .options(joinedload(DocumentChunk.document))
        .order_by(distance)
        .limit(limit)
    ).all()

    return [
        RetrievedChunk(
            chunk_id=chunk.id,
            document_id=chunk.document_id,
            title=chunk.document.title,
            source_name=chunk.document.source_name,
            content=chunk.content,
            score=1.0 - float(distance_value),
        )
        for chunk, distance_value in rows
    ]
