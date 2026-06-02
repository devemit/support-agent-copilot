# API Endpoint Reference

This project currently exposes 12 useful routes:

- 10 backend/API-style endpoints
- 2 frontend/navigation routes

Base local URL:

```text
http://localhost:8000
```

Interactive FastAPI docs:

```text
http://localhost:8000/docs
```

## Endpoint Summary

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/` | Redirects to the dashboard at `/app/`. |
| `GET` | `/app/` | Serves the static dashboard UI. |
| `GET` | `/health` | Checks if the API is running. |
| `GET` | `/documents` | Lists ingested knowledge-base documents. |
| `POST` | `/documents` | Creates a document from JSON text. |
| `POST` | `/documents/upload` | Uploads a `.txt` or `.md` document. |
| `POST` | `/tickets` | Creates and classifies a customer ticket. |
| `GET` | `/tickets/{ticket_id}` | Fetches one ticket by ID. |
| `POST` | `/tickets/{ticket_id}/draft` | Generates a cited AI draft for a ticket. |
| `POST` | `/drafts/{draft_id}/feedback` | Saves human feedback for a draft. |
| `POST` | `/dev/seed-sample-data` | Seeds sample knowledge-base docs. |
| `POST` | `/dev/reindex-documents` | Recomputes stored document embeddings. |

The core MVP API flow is:

```text
POST /dev/seed-sample-data
POST /tickets
POST /tickets/{ticket_id}/draft
POST /drafts/{draft_id}/feedback
```

## Frontend And Navigation

### `GET /`

Redirects to:

```text
/app/
```

Use this when you want the root URL to open the dashboard.

### `GET /app/`

Serves the static dashboard from:

```text
backend/app/static/
```

Files:

- `index.html`
- `styles.css`
- `app.js`

This is not a JSON API endpoint. It returns the browser UI.

## Health

### `GET /health`

Checks whether the FastAPI app is alive.

Response:

```json
{
  "status": "ok"
}
```

Used by:

- dashboard API status pill
- manual smoke testing
- deployment health checks

## Documents

Documents are the support knowledge base. The AI draft should be grounded in these sources.

### `GET /documents`

Lists all ingested documents.

Response example:

```json
[
  {
    "id": 1,
    "title": "Refund Policy",
    "source_name": "refund-policy.md",
    "chunk_count": 1,
    "created_at": "2026-06-02T18:00:00Z"
  }
]
```

Used by the dashboard to show:

- document count
- total chunk count
- stored document list

### `POST /documents`

Creates a document from JSON text.

Request:

```json
{
  "title": "Refund Policy",
  "source_name": "refund-policy.md",
  "content": "Customers are eligible for a refund when a duplicate charge is confirmed..."
}
```

What happens internally:

```text
content
-> split into chunks
-> create embeddings
-> save document
-> save document_chunks
```

Response:

```json
{
  "id": 1,
  "title": "Refund Policy",
  "source_name": "refund-policy.md",
  "chunk_count": 1,
  "created_at": "2026-06-02T18:00:00Z"
}
```

Common errors:

- `400`: content is too short or empty
- provider error if embedding generation fails

### `POST /documents/upload`

Uploads a `.txt` or `.md` file.

Request type:

```text
multipart/form-data
```

Form field:

```text
file
```

Accepted extensions:

```text
.txt
.md
```

What happens internally is the same as `POST /documents`:

```text
uploaded file
-> read UTF-8 text
-> split into chunks
-> create embeddings
-> save document
-> save document_chunks
```

Common errors:

- `400`: unsupported file type
- `400`: file is not UTF-8 text
- provider error if embedding generation fails

## Tickets

Tickets represent customer support issues.

### `POST /tickets`

Creates a ticket and immediately classifies it.

Request:

```json
{
  "customer_email": "customer@example.com",
  "subject": "Charged twice after upgrade",
  "body": "I upgraded my plan yesterday and was charged twice. Can you refund me?"
}
```

What happens internally:

```text
subject + body
-> send to LLM classification prompt
-> parse category, priority, sentiment, summary
-> save ticket
```

Response:

```json
{
  "id": 1,
  "customer_email": "customer@example.com",
  "subject": "Charged twice after upgrade",
  "body": "I upgraded my plan yesterday and was charged twice. Can you refund me?",
  "status": "open",
  "category": "billing",
  "priority": "high",
  "sentiment": "frustrated",
  "summary": "Customer reports a duplicate charge after upgrading their plan.",
  "created_at": "2026-06-02T18:00:00Z"
}
```

Used by:

- dashboard ticket form
- classification cards
- draft generation button state

Common errors:

- `422`: invalid request body
- provider error if Groq/OpenAI classification fails

### `GET /tickets/{ticket_id}`

Fetches one ticket.

Example:

```text
GET /tickets/1
```

Response is the same shape as `POST /tickets`.

Common errors:

- `404`: ticket not found

## Drafts

Drafts are AI-generated reply suggestions for human support agents.

### `POST /tickets/{ticket_id}/draft`

Generates a draft for a ticket.

Example:

```text
POST /tickets/1/draft
```

Request body:

```text
none
```

What happens internally:

```text
ticket subject + body
-> create query embedding
-> search document_chunks with pgvector
-> send ticket + retrieved chunks to LLM
-> parse draft JSON
-> save ai_draft
```

Response:

```json
{
  "id": 1,
  "ticket_id": 1,
  "content": "Hi, thanks for reaching out...",
  "citations": [
    {
      "document_id": 1,
      "chunk_id": 1,
      "title": "Refund Policy",
      "source_name": "refund-policy.md",
      "excerpt": "Customers are eligible for a refund when..."
    }
  ],
  "actions": [
    "Verify the customer account and recent billing events.",
    "Confirm whether the policy applies to this case."
  ],
  "confidence": 80,
  "model": "llama-3.3-70b-versatile",
  "created_at": "2026-06-02T18:00:00Z"
}
```

Used by:

- dashboard draft panel
- citations panel
- suggested actions list
- feedback form

Common errors:

- `404`: ticket not found
- `400`: no document chunks available
- provider error if LLM draft generation fails

## Feedback

Feedback records the human support agent's review of the AI draft.

### `POST /drafts/{draft_id}/feedback`

Saves whether the draft was accepted, edited, or rejected.

Example:

```text
POST /drafts/1/feedback
```

Request:

```json
{
  "rating": "accepted",
  "edited_content": null,
  "notes": "Looks good"
}
```

Allowed `rating` values:

```text
accepted
edited
rejected
```

If `rating` is `edited`, the dashboard sends the current edited draft text as `edited_content`.

Response:

```json
{
  "id": 1,
  "draft_id": 1,
  "rating": "accepted",
  "edited_content": null,
  "notes": "Looks good",
  "created_at": "2026-06-02T18:00:00Z"
}
```

Used by:

- dashboard feedback form
- future evaluation and quality tracking

Common errors:

- `404`: draft not found
- `422`: invalid rating value

## Development Helpers

These endpoints are useful during local development and demos.

### `POST /dev/seed-sample-data`

Loads sample docs from:

```text
backend/sample_docs/
```

Current sample docs:

- `account-access.md`
- `refund-policy.md`
- `subscription-plan-changes.md`

Response:

```json
{
  "documents_created": 0,
  "documents_skipped": 3
}
```

`documents_skipped` means the sample docs already exist.

Used by:

- dashboard `Seed Sample Docs` button
- quick local testing

### `POST /dev/reindex-documents`

Recomputes embeddings for every stored document chunk.

Use this when changing:

- `AI_PROVIDER`
- embedding model
- embedding implementation

Response:

```json
{
  "chunks_reindexed": 3
}
```

Important:

In `groq` mode, embeddings are still local/mock. In `openai` mode, this can call the OpenAI embeddings API and may require paid API quota.

## Dashboard Flow

The dashboard uses endpoints in this order:

```text
GET /health
GET /documents
POST /dev/seed-sample-data
POST /tickets
POST /tickets/{ticket_id}/draft
POST /drafts/{draft_id}/feedback
```

The usual user flow:

1. Open `/app/`.
2. Click `Seed Sample Docs`.
3. Load a sample ticket or type one manually.
4. Click `Create Ticket`.
5. Click `Generate Draft`.
6. Review citations and actions.
7. Click `Save Feedback`.

## Error Response Shape

FastAPI errors usually look like:

```json
{
  "detail": "Error message here"
}
```

Validation errors usually include a list in `detail`.

The frontend reads `detail` and shows it in a toast.
