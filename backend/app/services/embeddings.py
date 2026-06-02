import hashlib
import math
import re

from openai import OpenAI, OpenAIError

from app.config import get_settings
from app.services.errors import to_ai_provider_error


settings = get_settings()
TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9]+")


def embed_text(text: str) -> list[float]:
    # The rest of the app calls this single function, so providers can be swapped.
    if settings.ai_provider == "openai":
        return _embed_with_openai(text)
    return _embed_with_mock(text)


def _embed_with_openai(text: str) -> list[float]:
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is required when AI_PROVIDER=openai.")

    client = OpenAI(api_key=settings.openai_api_key)
    try:
        response = client.embeddings.create(
            model=settings.openai_embedding_model,
            input=text,
        )
    except OpenAIError as exc:
        raise to_ai_provider_error(exc) from exc
    return response.data[0].embedding


def _embed_with_mock(text: str) -> list[float]:
    # Local deterministic embedding for MVP testing. It is not a replacement for a real model.
    vector = [0.0] * settings.embedding_dimensions
    tokens = TOKEN_PATTERN.findall(text.lower())

    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % settings.embedding_dimensions
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[index] += sign

    # Normalize so cosine distance behaves consistently across short and long text.
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]
