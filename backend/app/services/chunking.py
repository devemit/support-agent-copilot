def chunk_text(text: str, chunk_size: int = 900, overlap: int = 150) -> list[str]:
    # Overlap keeps context from being lost at chunk boundaries.
    cleaned = " ".join(text.split())
    if not cleaned:
        return []

    chunks: list[str] = []
    start = 0
    while start < len(cleaned):
        end = min(start + chunk_size, len(cleaned))
        chunk = cleaned[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end == len(cleaned):
            break
        start = max(end - overlap, start + 1)

    return chunks
