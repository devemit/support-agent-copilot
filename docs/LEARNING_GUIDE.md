# AI Support Copilot Learning Guide

This guide explains how the MVP works and the main AI engineering concepts used in the project.

## What We Built

The app is a support agent copilot. A human support agent enters a customer ticket, and the system:

1. Classifies the ticket.
2. Searches support documents for relevant information.
3. Sends the ticket plus retrieved context to an LLM.
4. Generates a draft reply.
5. Shows citations and suggested actions.
6. Saves human feedback.

The main flow is:

```text
Knowledge docs -> chunks -> embeddings -> pgvector
Ticket -> classification -> retrieval -> LLM draft -> feedback
```

## What The Knowledge Panel Means

The **Knowledge** part of the dashboard is the support documentation that the AI is allowed to use.

Think of it as the company's source of truth:

```text
Refund policy
Subscription upgrade rules
Account access guide
Troubleshooting FAQ
Billing dispute process
```

When you click:

```text
Seed Sample Docs
```

the app loads sample documents from:

```text
backend/sample_docs/
```

For example:

```text
refund-policy.md
subscription-plan-changes.md
account-access.md
```

Then the backend does this:

```text
document text
-> split into smaller chunks
-> create embeddings for each chunk
-> store chunks in PostgreSQL/pgvector
```

Later, when a support ticket says:

```text
I was charged twice after upgrading.
```

the app searches the Knowledge Base and finds related chunks, such as:

```text
Refund Policy
Subscription Plan Changes
```

Those chunks are sent to the LLM along with the ticket.

Simple meaning:

```text
Ticket = what the customer says happened.
Knowledge = company rules the AI should use to help answer.
```

Without Knowledge docs, the AI can still write general text, but it will not know your company's actual policies.

## Chatbot vs Copilot

This project is not a customer-facing chatbot yet.

A customer-facing chatbot is usually this:

```text
Customer visits website
-> clicks robot/chat icon
-> chat modal opens
-> customer writes problem
-> AI replies directly to customer
```

That is a support chatbot.

What we built is this:

```text
Customer sends a ticket/email/chat message
-> human support agent opens this dashboard
-> agent enters or receives the customer message
-> AI helps the human understand and answer
-> human reviews the draft before sending it
```

That is a support copilot.

Simple difference:

```text
Chatbot = AI talks directly to the customer.
Copilot = AI helps the human support agent.
```

The copilot helps the support agent by:

- classifying the issue
- finding related company docs
- drafting a reply
- showing citations
- suggesting next actions
- saving feedback about the draft

This is safer for an MVP because a human checks the answer before it reaches the customer.

## How The AI Knows The Problem

The AI knows the problem because we send the customer's ticket text to it.

Example dashboard input:

```text
Subject:
Charged twice after upgrade

Message:
I upgraded my plan yesterday and was charged twice. Can you refund me?
```

The frontend sends this to the backend:

```json
{
  "subject": "Charged twice after upgrade",
  "body": "I upgraded my plan yesterday and was charged twice. Can you refund me?"
}
```

Then the backend sends a prompt to the model:

```text
Classify this customer support ticket.
Return category, priority, sentiment, and summary.

Subject: Charged twice after upgrade
Body: I upgraded my plan yesterday and was charged twice. Can you refund me?
```

The model reads the actual words:

```text
charged twice
upgrade
refund
```

From that, it understands that the issue is probably about billing.

So it can return:

```json
{
  "category": "billing",
  "priority": "high",
  "sentiment": "frustrated",
  "summary": "Customer reports a duplicate charge after upgrading their plan."
}
```

Important idea:

```text
Customer message tells the AI what happened.
Company docs tell the AI what the correct policy is.
The prompt tells the AI what format to return.
```

## Main Concepts

### Backend API

The backend is built with FastAPI. The frontend does not talk directly to Groq or OpenAI. It talks to our backend.

That is important because API keys must stay on the server, never in browser JavaScript.

```text
Browser dashboard
-> FastAPI backend
-> database / Groq / OpenAI-compatible API
```

### Database

The database is PostgreSQL running in Docker.

It also has the `pgvector` extension installed. That means it works as:

```text
normal relational database + vector database
```

Normal database examples:

- tickets
- documents
- drafts
- feedback

Vector database example:

- document chunk embeddings stored in `document_chunks.embedding`

### Embeddings

An embedding is a list of numbers that represents text meaning.

Example:

```text
"duplicate charge refund"
-> [0.12, -0.04, 0.88, ...]
```

Similar text should have similar vectors.

Embeddings do not directly make the LLM understand the ticket. The LLM understands the ticket by reading the text we send in the prompt.

Embeddings help our app search for relevant documents.

Example:

```text
Customer ticket:
"I was charged twice after upgrading."
```

The app turns that ticket into an embedding and searches stored document embeddings.

It should find documents with related meaning:

```text
Refund Policy
Billing Dispute Policy
Subscription Plan Changes
```

Then the app sends those documents to the LLM.

So the full flow is:

```text
Ticket text
-> embedding
-> vector search finds relevant docs
-> ticket + docs sent to LLM
-> LLM writes answer
```

A simple word example:

```text
sky
airplane
pilot
airport
flight
```

These concepts are related, so good embeddings should place them closer together than unrelated concepts like:

```text
refund
password
invoice
```

In our support app, these should be close:

```text
charged twice
duplicate payment
refund
billing issue
invoice problem
```

That is why vector search is useful. It searches by meaning, not only exact words.

In this project, documents are split into chunks and each chunk gets an embedding. Later, a ticket also gets an embedding, and the database searches for the closest document chunks.

Current setup:

- `mock` mode: local deterministic fake embeddings
- `groq` mode: still uses local mock embeddings
- `openai` mode: can use OpenAI embeddings, but that requires paid API quota

Groq is used for chat/classification/drafting, not embeddings.

Because Groq mode currently uses mock embeddings, retrieval is good enough for learning the architecture, but it is not as smart as production retrieval. A good future improvement is adding real free local embeddings with Ollama.

### Vector Search

Vector search means:

```text
Find document chunks whose embeddings are closest to the ticket embedding.
```

The code uses cosine distance:

```python
DocumentChunk.embedding.cosine_distance(query_embedding)
```

Lower distance means more similar.

### RAG

RAG means Retrieval-Augmented Generation.

Instead of asking the model to answer from memory, we first retrieve relevant support documents and then give those docs to the model.

The flow:

```text
Customer ticket
-> retrieve relevant docs
-> include docs in prompt
-> model drafts answer
```

This helps reduce hallucinations because the model is told to answer using retrieved context.

### Prompting

The LLM does not automatically know what our app wants. We tell it through prompts.

For classification, we say:

```text
Classify a customer support ticket.
Return compact JSON with keys: category, priority, sentiment, summary.
```

Then we send:

```text
Subject: Charged twice after upgrade
Body: I upgraded my plan yesterday and was charged twice. Can you refund me?
```

For draft generation, we say:

```text
You are a support agent copilot.
Draft a concise, helpful reply for a human agent to review.
Use only the provided context.
Return JSON with keys: content, actions, confidence, cited_chunk_ids.
```

Then we send the ticket plus retrieved document chunks.

### Structured Output

We ask the model to return JSON instead of plain text.

Example classification output:

```json
{
  "category": "billing",
  "priority": "high",
  "sentiment": "frustrated",
  "summary": "Customer reports duplicate charge after upgrading plan."
}
```

Example draft output:

```json
{
  "content": "Hi, thanks for reaching out...",
  "actions": [
    "Check invoice IDs",
    "Verify duplicate charge",
    "Escalate if older than 30 days"
  ],
  "confidence": 80,
  "cited_chunk_ids": [1, 2]
}
```

Structured output is useful because the backend can parse and save fields reliably.

## Folder Map

Important files:

```text
backend/app/main.py
```

Starts FastAPI, initializes the database, registers API routes, and serves the frontend.

```text
backend/app/config.py
```

Reads environment variables like `AI_PROVIDER`, `GROQ_API_KEY`, and model names.

```text
backend/app/db.py
```

Creates the database connection, enables `pgvector`, and creates tables.

```text
backend/app/models.py
```

Defines database tables:

- `Document`
- `DocumentChunk`
- `Ticket`
- `AIDraft`
- `Feedback`

```text
backend/app/schemas.py
```

Defines API request and response shapes using Pydantic.

```text
backend/app/api/documents.py
```

Document endpoints.

```text
backend/app/api/tickets.py
```

Ticket, draft, and feedback endpoints.

```text
backend/app/services/chunking.py
```

Splits support docs into smaller chunks.

```text
backend/app/services/embeddings.py
```

Creates embeddings for documents and tickets.

```text
backend/app/services/ingestion.py
```

Turns raw docs into chunks, embeddings, and database rows.

```text
backend/app/services/retrieval.py
```

Searches pgvector for document chunks relevant to a ticket.

```text
backend/app/services/llm.py
```

Calls mock, OpenAI, or Groq provider for classification and draft generation.

```text
backend/app/static/
```

Plain HTML/CSS/JavaScript dashboard.

## API Endpoints

For a complete endpoint-by-endpoint reference, read:

```text
docs/API_ENDPOINTS.md
```

### Health

```http
GET /health
```

Checks if the API is running.

### Seed Sample Docs

```http
POST /dev/seed-sample-data
```

Loads sample support docs from `backend/sample_docs`.

### Create Document

```http
POST /documents
```

Request:

```json
{
  "title": "Refund Policy",
  "source_name": "refund-policy.md",
  "content": "Customers are eligible for a refund when..."
}
```

What happens:

```text
content -> chunks -> embeddings -> save document_chunks
```

### Upload Document

```http
POST /documents/upload
```

Uploads a `.txt` or `.md` file.

### List Documents

```http
GET /documents
```

Returns stored documents and chunk counts.

### Create Ticket

```http
POST /tickets
```

Request:

```json
{
  "customer_email": "customer@example.com",
  "subject": "Charged twice after upgrade",
  "body": "I upgraded my plan yesterday and was charged twice. Can you refund me?"
}
```

What happens:

```text
ticket -> LLM classification -> save ticket
```

### Generate Draft

```http
POST /tickets/{ticket_id}/draft
```

What happens:

```text
ticket
-> embed ticket text
-> vector search document_chunks
-> send retrieved chunks + ticket to LLM
-> parse JSON output
-> save draft
```

### Save Feedback

```http
POST /drafts/{draft_id}/feedback
```

Request:

```json
{
  "rating": "accepted",
  "edited_content": null,
  "notes": "Looks good"
}
```

Allowed ratings:

```text
accepted
edited
rejected
```

Feedback is important because real AI products need evaluation data.

## Groq Usage

Groq is configured through `.env`:

```env
AI_PROVIDER=groq
GROQ_API_KEY=your_key_here
GROQ_BASE_URL=https://api.groq.com/openai/v1
GROQ_CHAT_MODEL=llama-3.3-70b-versatile
```

Groq provides an OpenAI-compatible API, so the code can use:

```python
OpenAI(api_key=settings.groq_api_key, base_url=settings.groq_base_url)
```

The model is used in:

```text
backend/app/services/llm.py
```

For:

- ticket classification
- draft generation

## Frontend Flow

Open:

```text
http://localhost:8000/app/
```

Test path:

1. Click `Seed Sample Docs`.
2. Fill customer email, subject, and message.
3. Click `Create Ticket`.
4. Click `Generate Draft`.
5. Review draft, citations, and actions.
6. Click `Save Feedback`.

You can ignore manual document fields at first.

## Database Inspection

Connect with:

```powershell
docker exec -it py-ai-db-1 psql -U support -d support_copilot
```

List tables:

```sql
\dt
```

View tickets:

```sql
SELECT id, customer_email, subject, category, priority, sentiment, created_at
FROM tickets
ORDER BY id DESC;
```

View documents:

```sql
SELECT id, title, source_name, created_at
FROM documents;
```

View chunks:

```sql
SELECT id, document_id, chunk_index, left(content, 120) AS preview
FROM document_chunks
ORDER BY id;
```

View drafts:

```sql
SELECT id, ticket_id, model, confidence, created_at
FROM ai_drafts
ORDER BY id DESC;
```

View feedback:

```sql
SELECT id, draft_id, rating, notes, created_at
FROM feedback
ORDER BY id DESC;
```

Exit:

```sql
\q
```

## What Happens When You Click Buttons

### Seed Sample Docs

Frontend calls:

```http
POST /dev/seed-sample-data
```

Backend reads files from:

```text
backend/sample_docs/
```

Then ingests them.

### Create Ticket

Frontend calls:

```http
POST /tickets
```

Backend calls Groq to classify the ticket, then saves it.

### Generate Draft

Frontend calls:

```http
POST /tickets/{ticket_id}/draft
```

Backend retrieves context from pgvector, sends that context to Groq, saves the draft, and returns it to the UI.

### Save Feedback

Frontend calls:

```http
POST /drafts/{draft_id}/feedback
```

Backend saves the human review.

## Current Limitations

This is an MVP, not a production system.

Current limitations:

- No login/authentication.
- No ticket history screen.
- No prompt versioning.
- No formal evaluation dashboard.
- Groq mode uses local mock embeddings.
- No real Zendesk/Intercom integration.
- No migrations tool like Alembic yet.
- No tests yet.

## Good Next Learning Steps

1. Add ticket history to the dashboard.
2. Add a draft history view.
3. Add real local embeddings with Ollama.
4. Add an evaluation dataset.
5. Add tests for ingestion, retrieval, and draft generation.
6. Add prompt versioning.
7. Add auth.
8. Add a real support platform integration.

## Mental Model

The most important idea:

```text
The model does not know your business data by itself.
Your database retrieves the relevant context.
Your prompt tells the model how to use that context.
Your backend validates and stores the result.
```

That is the core of many production AI applications.
