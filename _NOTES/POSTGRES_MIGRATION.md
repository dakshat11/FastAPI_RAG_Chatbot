# Migrating from SQLite to PostgreSQL
### For the RAG Voice Bot — `E:\Fastapi_voicebot`

---

## Why PostgreSQL over SQLite

SQLite is a single-file database. It works perfectly for one server process. The moment you run two instances (load balancer, Docker replicas, cloud deployment) each process has its own `chatbot.db` file — conversation history splits across instances and users get inconsistent responses.

PostgreSQL is a proper server — every instance connects to one shared database over the network. All conversation history lives in one place regardless of how many server instances are running.

| | SQLite (current) | PostgreSQL (new) |
|---|---|---|
| Where data lives | `chatbot.db` file on disk | PostgreSQL server |
| Multiple server instances | ❌ Each has own file | ✅ All share one DB |
| Concurrent writes | Limited | Full support |
| Production ready | ❌ | ✅ |
| Setup required | Zero | PostgreSQL server needed |

---

## What Changes in the Code

Only **2 files** change. Everything else — endpoints, schemas, agent logic, voice, RAG — is untouched.

---

## Step 1 — Install PostgreSQL locally (for development)

Download from [postgresql.org/download](https://www.postgresql.org/download/windows/)

During install:
- Set a password for the `postgres` superuser — remember this
- Default port is `5432` — leave it

After install, open **pgAdmin** or **psql** and create a database:
```sql
CREATE DATABASE voicebot;
```

> **Tip:** Keep the database name simple, no hyphens. `voicebot` or `voicebot_db` works well.

---

## Step 2 — Add credentials to `.env`

```
DATABASE_URL=postgresql://postgres:yourpassword@localhost:5432/voicebot
```

Format breakdown:
```
postgresql://  username  :  password  @  host  :  port  /  database_name
```

> **Important:** Never use the `postgres` superuser in production. Create a dedicated user:
> ```sql
> CREATE USER voicebot_user WITH PASSWORD 'strongpassword';
> GRANT ALL PRIVILEGES ON DATABASE voicebot TO voicebot_user;
> ```
> Then your URL becomes: `postgresql://voicebot_user:strongpassword@localhost:5432/voicebot`

---

## Step 3 — Add packages to `pyproject.toml`

```toml
"psycopg2-binary>=2.9.0",
"langgraph-checkpoint-postgres>=2.0.0",
```

Then run:
```bash
uv sync
```

> **Tip — `psycopg2-binary` vs `psycopg2`:**
> `psycopg2-binary` includes pre-compiled binaries — no C compiler needed. Use it for
> development and simple deployments. For production on Linux servers, use plain
> `psycopg2` which compiles against the system's libpq for better performance and
> fewer surprises.

---

## Step 4 — Add `database_url` to `core/config.py`

Inside the `Settings` class add one field:

```python
# PostgreSQL — set in .env
database_url: str = "postgresql://postgres:password@localhost:5432/voicebot"
```

Full updated `Settings` class for reference:

```python
class Settings(BaseSettings):
    # Required
    openai_api_key: str

    # Optional — override in .env
    model_name: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"
    sqlite_db_path: str = "../chatbot.db"  # no longer used after migration
    alpha_vantage_api_key: str = "C9PE94QUEW9VWGFM"
    chunk_size: int = 1000
    chunk_overlap: int = 200
    retriever_k: int = 4
    tts_voice: str = "alloy"

    # Pinecone
    pinecone_api_key: str
    pinecone_index_name: str = "voicebot"

    # PostgreSQL
    database_url: str = "postgresql://postgres:password@localhost:5432/voicebot"

    class Config:
        env_file = "../.env"
        env_file_encoding = "utf-8"
```

> **Tip:** Give it a default that matches your local dev setup so the app starts
> without `.env` during quick tests. In production, `.env` overrides it.

---

## Step 5 — Rewrite `core/database.py`

This is the only real logic change. Full new file:

```python
# core/database.py
# PostgreSQL connection and LangGraph checkpointer.
#
# Why PostgreSQL instead of SQLite?
# SQLite is a single file — multiple server instances each get their own copy.
# PostgreSQL is a server — all instances connect to one shared database.
#
# Why psycopg2 (synchronous) instead of asyncpg (async)?
# LangGraph's PostgresSaver uses psycopg2 under the hood.
# The LangGraph graph.invoke() call is already run in a thread pool by FastAPI
# so blocking I/O inside it is acceptable.

import psycopg2
from psycopg2.pool import ThreadedConnectionPool
from langgraph.checkpoint.postgres import PostgresSaver

from core.config import settings

# ThreadedConnectionPool manages a pool of reusable connections.
# minconn=1  — always keep at least 1 connection open
# maxconn=10 — never open more than 10 simultaneous connections
#
# Why a pool? Creating a new PostgreSQL connection takes ~50ms.
# A pool keeps connections open and reuses them — request latency stays low.
_pool = ThreadedConnectionPool(
    minconn=1,
    maxconn=10,
    dsn=settings.database_url,
)

# PostgresSaver wraps the pool with LangGraph's save/load interface.
# setup() creates the required tables in PostgreSQL if they don't exist yet.
checkpointer = PostgresSaver(_pool)
checkpointer.setup()    # safe to call every startup — checks before creating


def get_checkpointer() -> PostgresSaver:
    return checkpointer
```

> **Important — `checkpointer.setup()`:**
> This creates the LangGraph checkpoints tables in PostgreSQL on first run.
> It is safe to call on every startup — it checks before creating.
> Think of it as an automatic migration. You never need to create the tables manually.

> **Tip — connection pool size:**
> `maxconn=10` is a safe starting point. Each Uvicorn worker thread that hits the
> agent simultaneously needs one connection. For `--workers 4`, set `maxconn` to
> at least 8–12 to avoid connection starvation under load.

---

## Step 6 — `services/agent_service.py` — nothing changes

Open the file. The import is already:
```python
from core.database import checkpointer
```

And it is used as:
```python
return graph.compile(checkpointer=checkpointer)
```

Both lines stay exactly the same. `checkpointer` in `database.py` used to be a
`SqliteSaver` — now it is a `PostgresSaver`. The variable name and interface are
identical. `agent_service.py` does not know or care which one it is.

> **This is why the service layer pattern exists.** The agent only talks to the
> `checkpointer` interface. The concrete implementation (SQLite vs PostgreSQL) is
> isolated in `core/database.py`. One file changes, nothing else breaks.

---

## What the tables look like in PostgreSQL

After `checkpointer.setup()` runs, LangGraph creates these tables automatically:

```
checkpoints           — one row per graph invocation per thread
checkpoint_blobs      — serialised state (messages) per checkpoint
checkpoint_writes     — intermediate writes during a graph run
checkpoint_migrations — tracks which schema version is installed
```

You never interact with these tables directly — LangGraph manages them.
But they are useful for debugging:

```sql
-- See all thread IDs with saved conversations
SELECT DISTINCT thread_id FROM checkpoints;

-- Count messages per thread
SELECT thread_id, COUNT(*) FROM checkpoint_blobs GROUP BY thread_id;

-- Delete a specific thread's history
DELETE FROM checkpoints WHERE thread_id = 'my-thread';
```

---

## Verifying it works

Start the server and watch startup logs. If PostgreSQL connection fails, the error
appears immediately at startup — not on the first request — because
`_pool = ThreadedConnectionPool(...)` runs at import time.

```bash
uvicorn main:app --reload
```

**Successful startup:** server starts with no errors.

**Failed connection:**
```
psycopg2.OperationalError: could not connect to server: Connection refused
    Is the server running on host "localhost" and accepting TCP/IP connections on port 5432?
```

After a successful start, send a chat message and verify in PostgreSQL:
```sql
SELECT * FROM checkpoints LIMIT 5;
```
Rows should appear after each message.

---

## Common mistakes to avoid

**1. Wrong DATABASE_URL format**

```bash
# Wrong — missing protocol prefix
DATABASE_URL=localhost:5432/voicebot

# Wrong — using SQLite format
DATABASE_URL=sqlite:///chatbot.db

# Correct
DATABASE_URL=postgresql://user:password@localhost:5432/voicebot
```

**2. PostgreSQL service not running**

On Windows, PostgreSQL runs as a Windows Service. After a reboot it may not
auto-start. Check in `services.msc` that `postgresql-x64-16` (or your version) is
running before starting the app.

**3. Forgetting `checkpointer.setup()`**

Without it, LangGraph tries to read/write tables that don't exist:
```
psycopg2.errors.UndefinedTable: relation "checkpoints" does not exist
```

**4. Firewall blocking port 5432 in production**

Port `5432` is often blocked by cloud provider firewalls by default. Open it in
your security group rules, or use an SSH tunnel, or switch to a managed service
that handles this for you.

---

## For production (cloud deployment)

Use a managed PostgreSQL service instead of self-hosting:

| Service | Notes |
|---|---|
| **Supabase** | Free tier, great for small projects, gives you a `DATABASE_URL` directly |
| **Railway** | Simplest setup, one-click PostgreSQL, free tier available |
| **Neon** | Serverless PostgreSQL, free tier, scales to zero when idle |
| **AWS RDS** | Enterprise grade, most control, most expensive |

All of them give you a `DATABASE_URL` connection string. Paste it into `.env` and
the code works with zero other changes.

> **Tip:** Managed services handle backups, updates, failover, and SSL automatically.
> For anything beyond a local demo, always use a managed service over self-hosted
> PostgreSQL.

---

## Summary of all changes

| File | What changes |
|---|---|
| `.env` | Add `DATABASE_URL` |
| `pyproject.toml` | Add `psycopg2-binary`, `langgraph-checkpoint-postgres` |
| `core/config.py` | Add `database_url` field to `Settings` |
| `core/database.py` | Full rewrite — `ThreadedConnectionPool` + `PostgresSaver` |
| `services/agent_service.py` | **Nothing** — imports `checkpointer`, doesn't care what type |
| Everything else | **Nothing** |
