# RAG AI Agent — FastAPI Voice Chatbot

A production-structured AI agent backend built with **FastAPI**, **LangGraph**, **LangChain**, **Pinecone**, and **OpenAI**. Supports text and voice conversations, PDF document Q&A via Retrieval-Augmented Generation, web search, stock prices, and persistent multi-turn memory.

---

## Features

- **Text & Voice Chat** — Talk to the agent by typing or sending audio. Voice uses OpenAI Whisper (STT) and TTS for full speech in/out.
- **PDF RAG** — Upload a PDF and ask questions about it. Chunks are embedded and stored in Pinecone with per-thread namespace isolation.
- **Agentic Tools** — The LLM autonomously picks from: document retrieval, web search (DuckDuckGo), calculator, and live stock prices (Alpha Vantage).
- **Persistent Memory** — Conversation history survives server restarts via LangGraph's PostgreSQL checkpointer.
- **Multi-user Isolation** — Each `thread_id` gets its own Pinecone namespace and PostgreSQL checkpoint — no cross-session contamination.
- **Docker Compose** — One command starts the API + PostgreSQL.

---

## Tech Stack

| Layer | Technology |
|---|---|
| API | FastAPI + Uvicorn (ASGI) |
| Agent | LangGraph StateGraph + LangChain |
| LLM | OpenAI GPT-4o-mini |
| Embeddings | OpenAI text-embedding-3-small |
| Vector Store | Pinecone (cloud, namespace-isolated) |
| Database | PostgreSQL (LangGraph checkpointer) |
| Voice | OpenAI Whisper (STT) + OpenAI TTS |
| Containerisation | Docker + Docker Compose |

---

## Project Structure

```
├── api/v1/
│   ├── api.py               # Router aggregator
│   └── endpoints/
│       ├── chat.py          # POST /api/v1/chat
│       ├── pdf.py           # POST /api/v1/pdf/upload
│       ├── voice.py         # POST /api/v1/voice/chat
│       └── threads.py       # GET  /api/v1/threads
├── core/
│   ├── config.py            # pydantic-settings — reads .env
│   └── database.py          # PostgreSQL + LangGraph checkpointer
├── schemas/                 # Pydantic request/response models
├── services/
│   ├── agent_service.py     # LangGraph graph — the agent brain
│   ├── rag_service.py       # PDF ingestion + Pinecone retrieval
│   ├── voice_service.py     # Whisper STT + OpenAI TTS
│   └── tools.py             # calculator, stock price, web search
├── main.py                  # FastAPI app entry point
├── docker-compose.yml
└── Dockerfile
```

---

## Quick Start

### Prerequisites

- Docker Desktop
- OpenAI API key
- Pinecone API key + index named `voicebot`

### 1. Clone and configure

```bash
git clone https://github.com/your-username/Fastapi_voicebot.git
cd Fastapi_voicebot
```

Create a `.env` file (never commit this):

```env
OPENAI_API_KEY=sk-...
PINECONE_API_KEY=pcsk_...
PINECONE_INDEX_NAME=voicebot
DATABASE_URL=postgresql://voicebot_user:strongpassword@postgres:5432/voicebot
```

### 2. Run with Docker Compose

```bash
docker compose up --build
```

API: `http://localhost:8000`  
Swagger docs: `http://localhost:8000/docs`

### 3. Run locally (without Docker)

```bash
pip install uv
uv sync
uvicorn main:app --reload
```

> Requires a running PostgreSQL instance. Update `DATABASE_URL` in `.env`.

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Liveness check |
| POST | `/api/v1/chat` | Text chat with the agent |
| POST | `/api/v1/pdf/upload?thread_id=x` | Upload a PDF for RAG |
| POST | `/api/v1/voice/chat?thread_id=x` | Voice chat (audio in → audio out) |
| POST | `/api/v1/voice/transcribe-only` | Transcribe audio without agent |
| GET | `/api/v1/threads` | List all conversation threads |
| GET | `/api/v1/threads/{thread_id}` | Thread metadata and document status |

### Text Chat

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"thread_id": "my-session", "message": "What is the capital of France?"}'
```

### Upload PDF and ask about it

```bash
curl -X POST "http://localhost:8000/api/v1/pdf/upload?thread_id=my-session" \
  -F "file=@document.pdf"

curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"thread_id": "my-session", "message": "Summarise this document"}'
```

### Voice Chat

```bash
curl -X POST "http://localhost:8000/api/v1/voice/chat?thread_id=my-session" \
  -F "file=@question.mp3" \
  --output reply.mp3
```

---

## How the Agent Works

```
User message
    │
    ▼
LangGraph chat_node (LLM with tools)
    │
    ├── Needs tool? ──► ToolNode executes:
    │                     • rag_tool        — searches uploaded PDF
    │                     • search_tool     — DuckDuckGo web search
    │                     • calculator      — arithmetic
    │                     • get_stock_price — Alpha Vantage API
    │                   result fed back to LLM
    │
    └── Final answer ──► Response to user

State saved to PostgreSQL after every turn (survives restarts)
```

The `thread_id` parameter isolates each conversation — different threads have separate histories and separate PDF namespaces in Pinecone.

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `OPENAI_API_KEY` | ✅ | — | OpenAI API key |
| `PINECONE_API_KEY` | ✅ | — | Pinecone API key |
| `PINECONE_INDEX_NAME` | | `voicebot` | Pinecone index name |
| `DATABASE_URL` | | `postgresql://...` | PostgreSQL connection string |
| `MODEL_NAME` | | `gpt-4o-mini` | OpenAI chat model |
| `EMBEDDING_MODEL` | | `text-embedding-3-small` | OpenAI embedding model |
| `ALPHA_VANTAGE_API_KEY` | | — | For stock price tool |
| `TTS_VOICE` | | `alloy` | TTS voice (alloy/nova/echo/etc) |
| `CHUNK_SIZE` | | `1000` | PDF chunk size (characters) |
| `CHUNK_OVERLAP` | | `200` | PDF chunk overlap |
| `RETRIEVER_K` | | `4` | Number of chunks to retrieve |

---

## Architecture Decisions

**Why Pinecone over FAISS?** FAISS is in-memory — a server restart wipes all uploaded PDFs. Pinecone persists vectors in the cloud and supports namespace isolation, so each thread's documents are completely separate without provisioning separate indices.

**Why PostgreSQL over SQLite?** SQLite is a single file on disk — incompatible with multi-instance deployments. PostgreSQL allows all server replicas to share conversation history, making horizontal scaling possible.

**Why `Response` not `StreamingResponse` for audio?** `StreamingResponse` iterates over `BytesIO` by splitting on the `\n` byte (`0x0A`). MP3 binary data contains `0x0A` bytes throughout as audio data — not line endings. Splitting corrupts the file. `Response(content=bytes)` sends the buffer in one shot with no iteration.

---

