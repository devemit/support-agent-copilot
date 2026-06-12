from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import AIDraft, Feedback, Ticket
from app.schemas import DraftResponse, FeedbackCreate, FeedbackResponse, TicketCreate, TicketResponse
from app.services.errors import AIProviderError
from app.services.llm import classify_ticket, generate_support_draft
from app.services.retrieval import retrieve_relevant_chunks


router = APIRouter(tags=["tickets"])


@router.post("/tickets", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
def create_ticket(payload: TicketCreate, db: Session = Depends(get_db)) -> TicketResponse:
    workspace_id = _require_workspace_id(payload.workspace_id)
    # Classify immediately so the ticket is useful before a draft is generated.
    try:
        classification = classify_ticket(subject=payload.subject, body=payload.body)
    except AIProviderError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    ticket = Ticket(
        workspace_id=workspace_id,
        customer_email=str(payload.customer_email) if payload.customer_email else None,
        subject=payload.subject,
        body=payload.body,
        category=classification["category"],
        priority=classification["priority"],
        sentiment=classification["sentiment"],
        summary=classification["summary"],
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return _ticket_to_response(ticket)


@router.get("/tickets", response_model=list[TicketResponse])
def list_tickets(
    workspace_id: str | None = Query(default=None, max_length=100),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[TicketResponse]:
    workspace_id = _clean_workspace_id(workspace_id)
    if not workspace_id:
        return []

    tickets = db.scalars(
        select(Ticket).where(Ticket.workspace_id == workspace_id).order_by(Ticket.created_at.desc()).limit(limit)
    ).all()
    return [_ticket_to_response(ticket) for ticket in tickets]


@router.get("/tickets/{ticket_id}", response_model=TicketResponse)
def get_ticket(
    ticket_id: int,
    workspace_id: str | None = Query(default=None, max_length=100),
    db: Session = Depends(get_db),
) -> TicketResponse:
    ticket = _get_workspace_ticket(db=db, ticket_id=ticket_id, workspace_id=workspace_id)
    return _ticket_to_response(ticket)


@router.post("/tickets/{ticket_id}/draft", response_model=DraftResponse)
def create_draft(
    ticket_id: int,
    workspace_id: str | None = Query(default=None, max_length=100),
    db: Session = Depends(get_db),
) -> DraftResponse:
    ticket = _get_workspace_ticket(db=db, ticket_id=ticket_id, workspace_id=workspace_id)

    # This is the RAG step: turn the ticket into a search query and retrieve context.
    try:
        chunks = retrieve_relevant_chunks(db=db, query=f"{ticket.subject}\n{ticket.body}")
    except AIProviderError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    if not chunks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No document chunks available. Add knowledge-base documents first.",
        )

    # The generator receives only retrieved chunks, so the draft can cite its sources.
    try:
        generated = generate_support_draft(ticket=ticket, chunks=chunks)
    except AIProviderError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    draft = AIDraft(
        ticket_id=ticket.id,
        content=generated["content"],
        citations=generated["citations"],
        actions=generated["actions"],
        confidence=generated["confidence"],
        model=generated["model"],
    )
    db.add(draft)
    db.commit()
    db.refresh(draft)
    return _draft_to_response(draft)


@router.post("/drafts/{draft_id}/feedback", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
def create_feedback(
    draft_id: int,
    payload: FeedbackCreate,
    workspace_id: str | None = Query(default=None, max_length=100),
    db: Session = Depends(get_db),
) -> FeedbackResponse:
    # Feedback is the start of evaluation: did the human accept, edit, or reject the AI?
    workspace_id = _clean_workspace_id(workspace_id)
    if workspace_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Draft not found.")

    draft = db.scalar(
        select(AIDraft).join(AIDraft.ticket).where(AIDraft.id == draft_id, Ticket.workspace_id == workspace_id)
    )
    if draft is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Draft not found.")

    feedback = Feedback(
        draft_id=draft.id,
        rating=payload.rating,
        edited_content=payload.edited_content,
        notes=payload.notes,
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    return FeedbackResponse(
        id=feedback.id,
        draft_id=feedback.draft_id,
        rating=feedback.rating,
        edited_content=feedback.edited_content,
        notes=feedback.notes,
        created_at=feedback.created_at,
    )


def _clean_workspace_id(workspace_id: str | None) -> str | None:
    if workspace_id is None:
        return None
    workspace_id = workspace_id.strip()
    return workspace_id or None


def _require_workspace_id(workspace_id: str | None) -> str:
    workspace_id = _clean_workspace_id(workspace_id)
    if workspace_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="workspace_id is required for demo ticket isolation.",
        )
    return workspace_id


def _get_workspace_ticket(db: Session, ticket_id: int, workspace_id: str | None) -> Ticket:
    workspace_id = _clean_workspace_id(workspace_id)
    if workspace_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found.")

    ticket = db.scalar(select(Ticket).where(Ticket.id == ticket_id, Ticket.workspace_id == workspace_id))
    if ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found.")
    return ticket


def _ticket_to_response(ticket: Ticket) -> TicketResponse:
    return TicketResponse(
        id=ticket.id,
        customer_email=ticket.customer_email,
        subject=ticket.subject,
        body=ticket.body,
        status=ticket.status,
        category=ticket.category,
        priority=ticket.priority,
        sentiment=ticket.sentiment,
        summary=ticket.summary,
        created_at=ticket.created_at,
    )


def _draft_to_response(draft: AIDraft) -> DraftResponse:
    return DraftResponse(
        id=draft.id,
        ticket_id=draft.ticket_id,
        content=draft.content,
        citations=draft.citations,
        actions=draft.actions,
        confidence=draft.confidence,
        model=draft.model,
        created_at=draft.created_at,
    )
