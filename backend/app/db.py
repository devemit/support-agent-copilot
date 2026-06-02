from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.exc import ArgumentError
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


settings = get_settings()

def _normalize_database_url(database_url: str) -> str:
    url = database_url.strip().strip('"').strip("'")
    if not url:
        raise RuntimeError("DATABASE_URL is empty. Set it to your PostgreSQL/pgvector connection URL.")

    if url.startswith("${{") or url.startswith("{{"):
        raise RuntimeError(
            "DATABASE_URL still looks like an unresolved Railway reference. "
            "Set it from the database service reference, for example ${{Postgres.DATABASE_URL}}."
        )

    if url.startswith("postgresql+psycopg://"):
        return url
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)

    try:
        create_engine(url)
    except ArgumentError as exc:
        raise RuntimeError(
            "DATABASE_URL is not a valid SQLAlchemy database URL. "
            "Use the DATABASE_URL from your Railway pgvector/Postgres service."
        ) from exc

    return url


# One SQLAlchemy engine is shared by the app. pool_pre_ping avoids stale DB connections.
engine = create_engine(_normalize_database_url(settings.database_url), pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def init_db() -> None:
    # Import models here so SQLAlchemy knows all tables before create_all runs.
    from app import models  # noqa: F401

    with engine.begin() as connection:
        # pgvector adds the vector column type and vector similarity operators.
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    # FastAPI dependency: each request gets a DB session, then closes it.
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
