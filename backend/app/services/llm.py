import json

from openai import OpenAI, OpenAIError

from app.config import get_settings
from app.models import Ticket
from app.services.errors import AIProviderError, to_ai_provider_error
from app.services.retrieval import RetrievedChunk


settings = get_settings()


def classify_ticket(subject: str, body: str) -> dict[str, str]:
    # Provider switch: mock mode for local development, cloud providers for real AI.
    if settings.ai_provider == "openai":
        return _classify_with_openai(subject, body)
    if settings.ai_provider == "groq":
        return _classify_with_groq(subject, body)
    return _classify_with_mock(subject, body)


def generate_support_draft(ticket: Ticket, chunks: list[RetrievedChunk]) -> dict:
    # Draft generation is intentionally separated from retrieval for easier testing.
    if settings.ai_provider == "openai":
        return _draft_with_openai(ticket, chunks)
    if settings.ai_provider == "groq":
        return _draft_with_groq(ticket, chunks)
    return _draft_with_mock(ticket, chunks)


def _classify_with_mock(subject: str, body: str) -> dict[str, str]:
    text = f"{subject} {body}".lower()
    category = "general"
    if any(word in text for word in ["charge", "charged", "billing", "invoice", "refund", "payment"]):
        category = "billing"
    elif any(word in text for word in ["password", "login", "account", "sign in"]):
        category = "account_access"
    elif any(word in text for word in ["cancel", "subscription", "plan", "upgrade", "downgrade"]):
        category = "subscription"

    priority = "high" if any(word in text for word in ["twice", "urgent", "angry", "broken", "cannot"]) else "normal"
    sentiment = "frustrated" if any(word in text for word in ["charged", "angry", "upset", "not working"]) else "neutral"

    return {
        "category": category,
        "priority": priority,
        "sentiment": sentiment,
        "summary": body[:220],
    }


def _classify_with_openai(subject: str, body: str) -> dict[str, str]:
    client = _openai_client()
    return _classify_with_chat_client(client, settings.openai_chat_model, subject, body)


def _classify_with_groq(subject: str, body: str) -> dict[str, str]:
    client = _groq_client()
    return _classify_with_chat_client(client, settings.groq_chat_model, subject, body)


def _classify_with_chat_client(client: OpenAI, model: str, subject: str, body: str) -> dict[str, str]:
    try:
        response = client.chat.completions.create(
            model=model,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Classify a customer support ticket. Return compact JSON with keys: "
                        "category, priority, sentiment, summary. Use priority low, normal, high, or urgent."
                    ),
                },
                {"role": "user", "content": f"Subject: {subject}\n\nBody: {body}"},
            ],
        )
    except OpenAIError as exc:
        raise to_ai_provider_error(exc) from exc
    return _json_object(response.choices[0].message.content)


def _draft_with_mock(ticket: Ticket, chunks: list[RetrievedChunk]) -> dict:
    top_chunk = chunks[0]
    citations = [_citation_from_chunk(chunk) for chunk in chunks]
    actions = [
        "Verify the customer account and recent billing events.",
        "Confirm whether the policy source applies to this customer's case.",
        "Escalate to a specialist if billing records do not match the policy.",
    ]
    content = (
        f"Hi, thanks for reaching out. I understand your concern about {ticket.subject.lower()}. "
        f"Based on our support policy, {top_chunk.content[:350]} "
        "I will review the account details and help with the next eligible step."
    )
    return {
        "content": content,
        "citations": citations,
        "actions": actions,
        "confidence": 65,
        "model": "mock-support-copilot",
    }


def _draft_with_openai(ticket: Ticket, chunks: list[RetrievedChunk]) -> dict:
    client = _openai_client()
    return _draft_with_chat_client(client, settings.openai_chat_model, ticket, chunks)


def _draft_with_groq(ticket: Ticket, chunks: list[RetrievedChunk]) -> dict:
    client = _groq_client()
    return _draft_with_chat_client(client, settings.groq_chat_model, ticket, chunks)


def _draft_with_chat_client(client: OpenAI, model: str, ticket: Ticket, chunks: list[RetrievedChunk]) -> dict:
    # Give the model explicit chunk IDs so it can return citations we can verify.
    context = "\n\n".join(
        f"[chunk_id={chunk.chunk_id} document_id={chunk.document_id} title={chunk.title}]\n{chunk.content}"
        for chunk in chunks
    )
    try:
        response = client.chat.completions.create(
            model=model,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a support agent copilot. Draft a concise, helpful reply for a human "
                        "agent to review. Use only the provided context. If the context is insufficient, "
                        "say what the agent must verify. Return JSON with keys: content, actions, "
                        "confidence, cited_chunk_ids."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Ticket subject: {ticket.subject}\n"
                        f"Ticket body: {ticket.body}\n\n"
                        f"Retrieved context:\n{context}"
                    ),
                },
            ],
        )
    except OpenAIError as exc:
        raise to_ai_provider_error(exc) from exc
    payload = _json_object(response.choices[0].message.content)
    cited_ids = {int(chunk_id) for chunk_id in payload.get("cited_chunk_ids", []) if str(chunk_id).isdigit()}
    selected_chunks = [chunk for chunk in chunks if chunk.chunk_id in cited_ids] or chunks[:2]
    return {
        "content": str(payload.get("content", "")).strip(),
        "citations": [_citation_from_chunk(chunk) for chunk in selected_chunks],
        "actions": [str(action) for action in payload.get("actions", [])],
        "confidence": _confidence_value(payload.get("confidence")),
        "model": model,
    }


def _citation_from_chunk(chunk: RetrievedChunk) -> dict:
    # Store compact citation metadata instead of duplicating entire documents.
    return {
        "document_id": chunk.document_id,
        "chunk_id": chunk.chunk_id,
        "title": chunk.title,
        "source_name": chunk.source_name,
        "excerpt": chunk.content[:300],
    }


def _openai_client() -> OpenAI:
    if not settings.openai_api_key:
        raise AIProviderError("OPENAI_API_KEY is required when AI_PROVIDER=openai.", status_code=400)
    return OpenAI(api_key=settings.openai_api_key)


def _groq_client() -> OpenAI:
    if not settings.groq_api_key:
        raise AIProviderError("GROQ_API_KEY is required when AI_PROVIDER=groq.", status_code=400)
    return OpenAI(api_key=settings.groq_api_key, base_url=settings.groq_base_url)


def _json_object(content: str | None) -> dict:
    if not content:
        return {}
    return json.loads(content)


def _confidence_value(value: object) -> int:
    try:
        confidence = int(value)
    except (TypeError, ValueError):
        return 50

    if confidence < 1:
        return 50
    return min(confidence, 100)
