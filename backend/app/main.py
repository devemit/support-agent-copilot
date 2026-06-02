from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.api import dev, documents, tickets
from app.db import init_db


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    # Create tables and enable pgvector when the API container starts.
    init_db()
    yield


app = FastAPI(
    title="AI Support Copilot MVP",
    version="0.1.0",
    description="Backend MVP for cited support-ticket draft generation.",
    lifespan=lifespan,
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/")
def root() -> RedirectResponse:
    return RedirectResponse(url="/app/")


app.include_router(documents.router)
app.include_router(tickets.router)
app.include_router(dev.router)

static_dir = Path(__file__).resolve().parent / "static"
app.mount("/app", StaticFiles(directory=static_dir, html=True), name="frontend")
