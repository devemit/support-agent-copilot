# AI Support Copilot MVP

A backend-first MVP for a support agent copilot. It ingests support documents, creates customer tickets, retrieves relevant knowledge-base chunks, and drafts cited replies for a human agent to review.

## Stack

- FastAPI
- PostgreSQL + pgvector
- SQLAlchemy
- Static HTML/CSS/JavaScript frontend served by FastAPI
- Docker Compose
- Mock AI provider by default
- Optional OpenAI provider through environment variables

## Quick Start

1. Copy the environment file:

```powershell
Copy-Item .env.example .env
```

2. Start the database and API:

```powershell
docker compose up --build
```

3. Open the API docs:

```text
http://localhost:8000/docs
```

Or open the agent dashboard:

```text
http://localhost:8000/app/
```

4. Seed sample knowledge-base docs:

```powershell
Invoke-RestMethod -Method Post http://localhost:8000/dev/seed-sample-data
```

5. Create a ticket:

```powershell
$ticket = Invoke-RestMethod -Method Post http://localhost:8000/tickets `
  -ContentType "application/json" `
  -Body '{"customer_email":"customer@example.com","subject":"Charged twice","body":"I upgraded my plan yesterday and was charged twice. Can you refund me?"}'
```

6. Generate a cited draft:

```powershell
Invoke-RestMethod -Method Post "http://localhost:8000/tickets/$($ticket.id)/draft"
```

## OpenAI Mode

The project works in mock mode without an API key. To use a real model, edit `.env`:

```env
AI_PROVIDER=openai
OPENAI_API_KEY=your_api_key_here
OPENAI_CHAT_MODEL=gpt-4o-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
```

Then restart:

```powershell
docker compose up --build
```

If you already seeded documents while using `AI_PROVIDER=mock`, reindex them after switching to OpenAI:

```powershell
Invoke-RestMethod -Method Post http://localhost:8000/dev/reindex-documents
```

That recomputes stored document embeddings with the active embedding provider.

## Groq Mode

Groq can be used for ticket classification and draft generation through its OpenAI-compatible API. Document embeddings still use the local mock embedding function in this mode, so Groq mode is useful for free/low-cost LLM testing but is not a full production-grade semantic retrieval setup yet.

1. Create a Groq API key:

```text
https://console.groq.com/keys
```

2. Edit `.env`:

```env
AI_PROVIDER=groq
GROQ_API_KEY=your_groq_key_here
GROQ_BASE_URL=https://api.groq.com/openai/v1
GROQ_CHAT_MODEL=llama-3.3-70b-versatile
```

3. Restart the API:

```powershell
docker compose up -d --force-recreate api
```

## MVP API

- `GET /health`
- `POST /documents`
- `POST /documents/upload`
- `GET /documents`
- `POST /tickets`
- `GET /tickets/{ticket_id}`
- `POST /tickets/{ticket_id}/draft`
- `POST /drafts/{draft_id}/feedback`
- `POST /dev/seed-sample-data`
- `POST /dev/reindex-documents`

## Folder Structure

```text
.
├── .env                          Local environment values used by Docker Compose
├── .env.example                  Safe template showing required environment variables
├── .gitignore                    Files Git should ignore, such as .env and caches
├── docker-compose.yml            Runs the FastAPI API and PostgreSQL/pgvector locally
├── docs/
│   ├── LEARNING_GUIDE.md         Explains concepts, flow, APIs, prompts, and database usage
│   └── LOCAL_VS_DEPLOYED.md      Explains local Docker setup vs deployed Railway-style setup
├── README.md                     Project setup, usage notes, and architecture overview
└── backend/
    ├── .dockerignore             Files Docker should not copy into the API image
    ├── Dockerfile                Builds the FastAPI API container image
    ├── requirements.txt          Python dependencies installed inside the API image
    ├── sample_docs/
    │   ├── account-access.md             Sample support doc about login/account issues
    │   ├── refund-policy.md              Sample support doc about refunds and duplicate charges
    │   └── subscription-plan-changes.md  Sample support doc about upgrades/downgrades
    └── app/
        ├── __init__.py           Marks app/ as a Python package
        ├── config.py             Loads settings from environment variables
        ├── db.py                 Creates DB engine, sessions, tables, and pgvector extension
        ├── main.py               Creates the FastAPI app and registers route modules
        ├── models.py             SQLAlchemy database tables and relationships
        ├── schemas.py            Pydantic request and response validation models
        ├── api/
        │   ├── __init__.py       Marks api/ as a Python package
        │   ├── dev.py            Development helper endpoints, such as sample-data seeding
        │   ├── documents.py      Endpoints for creating, uploading, and listing documents
        │   └── tickets.py        Endpoints for tickets, AI drafts, and feedback
        ├── static/
        │   ├── app.js            Browser-side logic that calls the FastAPI endpoints
        │   ├── index.html        Dashboard markup for the support copilot UI
        │   └── styles.css        Dashboard layout, forms, panels, and responsive styling
        └── services/
            ├── __init__.py       Marks services/ as a Python package
            ├── chunking.py       Splits long documents into overlapping text chunks
            ├── embeddings.py     Creates mock or OpenAI embeddings for text
            ├── ingestion.py      Converts documents into chunks + embeddings and stores them
            ├── llm.py            Classifies tickets and generates support draft replies
            └── retrieval.py      Searches pgvector for chunks relevant to a ticket
```

The MVP flow is split like this:

```text
api/ receives HTTP requests
-> services/ performs ingestion, retrieval, and generation
-> models.py defines what gets saved
-> db.py connects everything to PostgreSQL/pgvector
```

### Root Files

`.env` contains local runtime values. It is intentionally ignored by Git because it can contain secrets like `OPENAI_API_KEY`.

`.env.example` is the safe template to copy when setting up the project on another machine.

`docker-compose.yml` starts two services:

- `db`: PostgreSQL with the `pgvector` extension, used as both a normal database and vector database.
- `api`: FastAPI backend, mounted with reload enabled for local development.

### Backend App Files

`app/main.py` is the API entrypoint. It creates the FastAPI app, initializes the database on startup, exposes `/health`, and includes the route modules.

`app/config.py` centralizes configuration. The rest of the app reads settings like `AI_PROVIDER`, `DATABASE_URL`, `OPENAI_CHAT_MODEL`, and `RETRIEVAL_TOP_K` from here.

`app/db.py` manages database setup. It creates the SQLAlchemy engine, opens/closes request sessions, enables the `vector` extension, and creates tables.

`app/models.py` defines what is stored in PostgreSQL:

- `Document`: one uploaded or manually created knowledge-base document.
- `DocumentChunk`: one searchable text chunk with an embedding vector.
- `Ticket`: one customer support request.
- `AIDraft`: one generated support reply with citations and suggested actions.
- `Feedback`: one human review of a draft.

`app/schemas.py` defines the API input/output shapes. FastAPI uses these models to validate requests and format responses.

### Frontend Files

The frontend is intentionally simple for the MVP: plain HTML, CSS, and JavaScript served by FastAPI at `http://localhost:8000/app/`.

`app/static/index.html` defines the dashboard structure:

- knowledge-base panel
- document forms
- ticket composer
- classification display
- draft review panel
- citations, actions, and feedback form

`app/static/styles.css` contains the dashboard layout and responsive styling. It keeps the UI work-focused and compact instead of looking like a landing page.

`app/static/app.js` contains browser-side behavior:

- checks API health
- loads documents
- seeds sample docs
- creates documents
- uploads `.txt` and `.md` files
- creates tickets
- generates drafts
- renders citations and suggested actions
- saves feedback

### API Modules

`app/api/documents.py` handles knowledge-base document endpoints:

- `POST /documents`: create a document from JSON text.
- `POST /documents/upload`: upload a `.txt` or `.md` file.
- `GET /documents`: list ingested documents.

`app/api/tickets.py` handles the main copilot workflow:

- `POST /tickets`: create and classify a support ticket.
- `GET /tickets/{ticket_id}`: fetch a ticket.
- `POST /tickets/{ticket_id}/draft`: retrieve relevant docs and generate a cited draft.
- `POST /drafts/{draft_id}/feedback`: save human feedback.

`app/api/dev.py` contains development-only helpers. Right now it seeds the sample docs from `backend/sample_docs` and can reindex document embeddings after changing AI providers or embedding models.

### Service Modules

`app/services/chunking.py` cleans and splits long support documents. Chunks overlap slightly so useful context is not lost between chunks.

`app/services/embeddings.py` turns text into vectors. In `mock` mode it creates deterministic local vectors for development. In `openai` mode it calls the OpenAI embeddings API.

`app/services/ingestion.py` is the document ingestion pipeline:

```text
raw document text -> chunks -> embeddings -> document_chunks table
```

`app/services/retrieval.py` is the vector search pipeline:

```text
ticket text -> embedding -> pgvector cosine search -> relevant chunks
```

`app/services/llm.py` is the AI generation layer. It classifies tickets and generates support drafts. The rest of the app calls this module without needing to know whether the provider is mock or OpenAI.

## What To Build Next

- Read `docs/LEARNING_GUIDE.md` and trace one request through the code
- Read `docs/LOCAL_VS_DEPLOYED.md` to understand local vs hosted runtime
- Ticket history and draft history views
- Prompt and retrieval evaluation set
- Agent edit tracking
- Authentication
- Real Zendesk/Intercom import
