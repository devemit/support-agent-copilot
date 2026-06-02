# AI Support Copilot

An internal support-agent copilot that helps human support agents understand customer tickets, retrieve relevant knowledge-base policy, and draft cited replies for review.

Live demo:

```text
https://support-agent-copilot-production.up.railway.app/app/
```

API docs:

```text
https://support-agent-copilot-production.up.railway.app/docs
```

## What It Does

This is not a customer-facing chatbot. It is an internal dashboard for a support agent.

The workflow:

```text
Support docs -> chunks -> embeddings -> pgvector
Customer ticket -> classification -> retrieval -> AI draft -> human feedback
```

The app helps a support agent:

- load company/support knowledge such as refund policies, billing rules, and account access guides
- create a customer support ticket
- classify the ticket by category, priority, sentiment, and summary
- retrieve relevant knowledge-base chunks using vector search
- generate a support reply draft with citations
- review suggested next actions
- save feedback: accepted, edited, or rejected

## Demo Flow

Open the live app and test:

```text
Seed Sample Docs
-> Billing Sample
-> Create Ticket
-> Generate Draft
-> Save Feedback
```

The `Knowledge Base` panel contains source documents the AI is allowed to use. The ticket text tells the AI what the customer problem is; the retrieved knowledge docs tell the AI what company policy applies.

## Tech Stack

- FastAPI
- PostgreSQL + pgvector
- SQLAlchemy
- Groq API for ticket classification and draft generation
- Static HTML/CSS/JavaScript dashboard served by FastAPI
- Docker and Docker Compose
- Railway deployment

Current AI setup:

- `groq` mode uses Groq for LLM responses
- embeddings are local/mock in Groq mode for MVP learning purposes
- `openai` mode supports OpenAI embeddings/chat if API billing is available

## Local Setup

1. Copy the environment template:

```powershell
Copy-Item .env.example .env
```

2. Add your Groq key to `.env`:

```env
AI_PROVIDER=groq
GROQ_API_KEY=your_groq_key_here
GROQ_BASE_URL=https://api.groq.com/openai/v1
GROQ_CHAT_MODEL=llama-3.3-70b-versatile
```

3. Start the app and database:

```powershell
docker compose up --build
```

4. Open:

```text
http://localhost:8000/app/
```

API docs:

```text
http://localhost:8000/docs
```

## Environment Variables

Local `.env` example:

```env
AI_PROVIDER=groq
DATABASE_URL=postgresql+psycopg://support:support@db:5432/support_copilot

GROQ_API_KEY=your_groq_key_here
GROQ_BASE_URL=https://api.groq.com/openai/v1
GROQ_CHAT_MODEL=llama-3.3-70b-versatile

EMBEDDING_DIMENSIONS=1536
RETRIEVAL_TOP_K=5
```

Important:

```text
.env = private local secrets
.env.example = safe public template
```

Never commit real API keys.

## API Summary

Core endpoints:

```text
GET  /health
GET  /documents
POST /documents
POST /documents/upload
POST /tickets
GET  /tickets/{ticket_id}
POST /tickets/{ticket_id}/draft
POST /drafts/{draft_id}/feedback
POST /dev/seed-sample-data
POST /dev/reindex-documents
```

Main dashboard flow:

```text
POST /dev/seed-sample-data
POST /tickets
POST /tickets/{ticket_id}/draft
POST /drafts/{draft_id}/feedback
```

## Project Structure

```text
.
├── .env.example
├── .gitignore
├── docker-compose.yml
├── railway.json
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── start.sh
│   ├── sample_docs/
│   └── app/
│       ├── main.py
│       ├── config.py
│       ├── db.py
│       ├── models.py
│       ├── schemas.py
│       ├── api/
│       ├── services/
│       └── static/
```

Important parts:

- `backend/app/api/`: FastAPI route handlers
- `backend/app/services/`: ingestion, embeddings, retrieval, and LLM logic
- `backend/app/static/`: dashboard HTML/CSS/JS
- `backend/sample_docs/`: sample support knowledge-base documents
- `docker-compose.yml`: local API + PostgreSQL/pgvector
- `railway.json`: Railway Docker deployment config

## Railway Deployment

The app is deployed on Railway using:

```text
railway.json -> backend/Dockerfile -> backend/start.sh
```

Required Railway app-service variables:

```env
AI_PROVIDER=groq
GROQ_API_KEY=your_groq_key_here
GROQ_BASE_URL=https://api.groq.com/openai/v1
GROQ_CHAT_MODEL=llama-3.3-70b-versatile
EMBEDDING_DIMENSIONS=1536
RETRIEVAL_TOP_K=5
DATABASE_URL=${{YourPgvectorService.DATABASE_URL}}
```

Use a Railway PostgreSQL/pgvector database service. Do not use the local Docker database URL on Railway:

```env
DATABASE_URL=postgresql+psycopg://support:support@db:5432/support_copilot
```

The `db` hostname only exists inside local Docker Compose.

## Database

The database stores:

- `documents`
- `document_chunks`
- `tickets`
- `ai_drafts`
- `feedback`

`document_chunks.embedding` is a pgvector column used for similarity search.

Local pgAdmin connection:

```text
Host: 127.0.0.1
Port: 5432
Database: support_copilot
User: support
Password: support
```

## Current Limitations

- No authentication yet
- No ticket history screen yet
- No formal evaluation dashboard yet
- Groq mode still uses mock/local embeddings
- No real Zendesk/Intercom integration yet
- No Alembic migrations yet

## Next Improvements

- Ticket and draft history
- Real local embeddings with Ollama
- Evaluation dashboard
- Prompt versioning
- Agent edit tracking
- Authentication
- Real support-platform integration
