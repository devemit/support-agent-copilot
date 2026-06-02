from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class DocumentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    source_name: str | None = Field(default=None, max_length=255)
    content: str = Field(min_length=20)


class DocumentResponse(BaseModel):
    id: int
    title: str
    source_name: str | None
    chunk_count: int
    created_at: datetime


class TicketCreate(BaseModel):
    customer_email: EmailStr | None = None
    subject: str = Field(min_length=1, max_length=255)
    body: str = Field(min_length=5)


class TicketResponse(BaseModel):
    id: int
    customer_email: str | None
    subject: str
    body: str
    status: str
    category: str | None
    priority: str | None
    sentiment: str | None
    summary: str | None
    created_at: datetime


class Citation(BaseModel):
    document_id: int
    chunk_id: int
    title: str
    source_name: str | None = None
    excerpt: str


class DraftResponse(BaseModel):
    id: int
    ticket_id: int
    content: str
    citations: list[Citation]
    actions: list[str]
    confidence: int
    model: str
    created_at: datetime


class FeedbackCreate(BaseModel):
    rating: Literal["accepted", "edited", "rejected"]
    edited_content: str | None = None
    notes: str | None = None


class FeedbackResponse(BaseModel):
    id: int
    draft_id: int
    rating: str
    edited_content: str | None
    notes: str | None
    created_at: datetime
