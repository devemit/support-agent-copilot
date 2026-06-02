from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


settings = get_settings()

# One SQLAlchemy engine is shared by the app. pool_pre_ping avoids stale DB connections.
engine = create_engine(settings.database_url, pool_pre_ping=True)
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
