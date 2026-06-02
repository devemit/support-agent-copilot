# Local vs Deployed App

This note explains how the app works on your machine now, and how it would work if deployed to a platform like Railway.

## Current Local Setup

Right now the app runs on your own computer.

The main file for local infrastructure is:

```text
docker-compose.yml
```

It starts two Docker containers:

```text
api = FastAPI backend
db  = PostgreSQL + pgvector
```

Local architecture:

```text
Your browser
-> http://localhost:8000/app/
-> FastAPI container
-> PostgreSQL/pgvector container
-> Groq API
```

## What Docker Does Locally

Docker gives us a repeatable local environment.

Without Docker, you would need to manually install:

- Python
- FastAPI dependencies
- PostgreSQL
- pgvector extension
- database users/passwords

With Docker Compose, one command starts everything:

```powershell
docker compose up --build
```

The API container is built from:

```text
backend/Dockerfile
```

The database container uses:

```text
pgvector/pgvector:pg16
```

That image is PostgreSQL with pgvector already installed.

## Local URLs

Dashboard:

```text
http://localhost:8000/app/
```

API docs:

```text
http://localhost:8000/docs
```

PostgreSQL connection from your computer:

```text
Host: 127.0.0.1
Port: 5432
Database: support_copilot
User: support
Password: support
```

PostgreSQL connection from inside Docker:

```text
Host: db
Port: 5432
Database: support_copilot
User: support
Password: support
```

Inside Docker, the API uses:

```env
DATABASE_URL=postgresql+psycopg://support:support@db:5432/support_copilot
```

The host is `db` because `db` is the Docker Compose service name.

## Local Data

The local database stores data in a Docker volume:

```text
postgres-data
```

This means your local tickets, documents, drafts, and feedback survive container restarts.

But this data is still local to your machine.

If you deploy to Railway, this data does not automatically move.

## Current Local Flow

When you use the dashboard locally:

```text
Browser
-> FastAPI backend on localhost:8000
-> local PostgreSQL/pgvector container
-> Groq API for classification/draft generation
```

The local database stores:

- documents
- document chunks
- embeddings
- tickets
- AI drafts
- feedback

Groq handles:

- ticket classification
- draft generation

The browser never talks directly to Groq. The backend talks to Groq.

That keeps the API key private.

## Deployed Setup

If we deploy to Railway, the app no longer runs from your laptop.

Instead:

```text
GitHub repo
-> Railway builds the app
-> Railway runs the API
-> Railway hosts the database
-> Railway gives you a public URL
```

Deployed architecture:

```text
User browser
-> https://your-app.up.railway.app/app/
-> Railway FastAPI service
-> Railway PostgreSQL/pgvector service
-> Groq API
```

Your laptop becomes the development machine. Railway becomes the demo/production machine.

## What Moves To Railway

These move to Railway:

- application code
- FastAPI backend
- frontend static files
- Dockerfile build
- environment variables
- hosted database

These do not automatically move:

- local `.env`
- local Docker volume
- local database rows
- local test tickets
- local sample-ingested docs

If you want the same docs in Railway, you seed them again or migrate/export the data.

## Railway Deployment Model

Railway usually works like this:

1. Push code to GitHub.
2. Create a Railway project.
3. Connect Railway to the GitHub repo.
4. Railway detects/builds the backend.
5. Add a PostgreSQL/pgvector database service.
6. Set environment variables in Railway.
7. Deploy.
8. Open the public Railway URL.

Railway can build from a Dockerfile. In our case, the Dockerfile is:

```text
backend/Dockerfile
```

Because our Dockerfile is inside `backend/`, Railway may need to be told the Dockerfile path.

## Railway Environment Variables

Railway does not use your local `.env` file automatically.

You set variables in Railway's dashboard.

For our app:

```env
AI_PROVIDER=groq
GROQ_API_KEY=your_groq_key_here
GROQ_BASE_URL=https://api.groq.com/openai/v1
GROQ_CHAT_MODEL=llama-3.3-70b-versatile
EMBEDDING_DIMENSIONS=1536
RETRIEVAL_TOP_K=5
```

Railway also provides a database connection variable.

It is usually called:

```env
DATABASE_URL
```

Our backend reads `DATABASE_URL`, so it can connect to Railway's database instead of the local Docker database.

## Important pgvector Detail

Our app needs PostgreSQL with pgvector.

Standard PostgreSQL is not enough because this app stores vectors:

```text
document_chunks.embedding
```

So on Railway, use a PostgreSQL service/template that supports pgvector.

If the database does not support pgvector, app startup will fail when it runs:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

## Local vs Deployed Comparison

| Part | Local | Deployed |
| --- | --- | --- |
| App URL | `localhost:8000/app/` | Railway public URL |
| API runtime | Docker container on your PC | Railway service |
| Database | Docker Postgres container | Railway Postgres/pgvector |
| Secrets | local `.env` | Railway variables |
| Data | local Docker volume | Railway database volume/storage |
| Groq calls | from local API container | from Railway API service |
| Browser access | only your machine unless exposed | public URL |

## Simple Mental Model

Local:

```text
Everything runs on your machine.
```

Deployed:

```text
Code runs on Railway.
Database runs on Railway.
Users access it through a public URL.
Groq is still called as an external AI API.
```

## What Would Need To Change Before Deploying

Before deploying, we adjusted:

1. Added `railway.json` so Railway builds from `backend/Dockerfile`.
2. Added `backend/start.sh` so the app listens on Railway's `PORT` variable.

Before a real Railway deploy, still do this:

1. Use Railway's `DATABASE_URL`.
2. Use a pgvector-capable Postgres service.
3. Set `GROQ_API_KEY` in Railway variables.
4. Seed documents in the deployed database.
5. Avoid exposing the database publicly unless needed.

## Why Deploy

Deploying is useful because:

- you can show the project with a real URL
- it proves you understand production environments
- it separates local development from hosted runtime
- it makes the project stronger for a portfolio

## Summary

Current local app:

```text
Browser -> local Docker API -> local Docker Postgres/pgvector -> Groq
```

Deployed app:

```text
Browser -> Railway API -> Railway Postgres/pgvector -> Groq
```

Same app idea, different place where it runs.
