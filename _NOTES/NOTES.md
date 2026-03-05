# Building a Production FastAPI AI Agent from Scratch
### RAG Chatbot + Agentic Tools + Voice Interface — Step by Step

> This guide builds your exact working project (`voice_agent_placement`) from a blank
> directory to a fully featured voice-enabled RAG agent. Every concept is introduced
> at the moment it is needed. Every code block is the actual working code in your project.

---

## Table of Contents

- [Phase 0 — Project Setup](#phase-0--project-setup)
- [Phase 1 — FastAPI Foundations You Must Understand First](#phase-1--fastapi-foundations)
- [Phase 2 — Basic Chatbot (No Memory, No Tools)](#phase-2--basic-chatbot)
- [Phase 3 — Adding Persistence (Conversation Memory)](#phase-3--adding-persistence)
- [Phase 4 — Adding Agentic Tools](#phase-4--adding-agentic-tools)
- [Phase 5 — Adding RAG (PDF Knowledge)](#phase-5--adding-rag)
- [Phase 6 — Adding Voice Interface](#phase-6--adding-voice-interface)
- [Final State — All Endpoints](#final-state--all-endpoints)
- [Interview Talking Points](#interview-talking-points)

---

## Phase 0 — Project Setup

Every professional Python project starts with three things before a single line of
application code is written: an isolated environment, a dependency manifest, and a
clear directory structure.

### Step 0.1 — Virtual Environment

A virtual environment is an isolated copy of Python where your project's dependencies
live. Without it, every project on your machine shares the same Python installation and
you will eventually get version conflicts that are nearly impossible to debug.

```bash
# Create the project directory
mkdir voice_agent_placement
cd voice_agent_placement

# Option A — using uv (faster, modern, what your project uses)
pip install uv
uv venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Mac/Linux

# Option B — using standard Python venv
python -m venv .venv
.venv\Scripts\activate          # Windows
```

You know the venv is active when your terminal prompt shows `(.venv)` at the start.
From this point, every `pip install` or `uv add` installs into the venv, not your system Python.

**Rule:** Never install packages into system Python for a project. Always activate the venv first.

### Step 0.2 — Dependency Manifest (`pyproject.toml`)

`pyproject.toml` is the modern Python standard for declaring project metadata and
dependencies. It replaces the old `requirements.txt` for managed projects.

```toml
# pyproject.toml
[project]
name = "voice-agent-placement"
version = "0.1.0"
description = "RAG AI Agent — FastAPI backend with LangGraph, FAISS, and OpenAI"
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    # Web framework
    "fastapi[standard]>=0.129.0",
    "python-multipart>=0.0.9",        # Required for File() and Form() uploads

    # LangChain ecosystem
    "langchain>=1.2.10",
    "langchain-community>=0.4.1",
    "langchain-openai>=1.1.10",
    "langchain-text-splitters>=0.3.0",

    # LangGraph + checkpointing
    "langgraph[checkpoint]>=1.0.9",
    "langgraph-checkpoint>=4.0.0",
    "langgraph-checkpoint-sqlite>=3.0.3",

    # Vector store
    "faiss-cpu>=1.13.2",

    # PDF loading
    "pypdf>=6.7.1",

    # Settings management
    "pydantic-settings>=2.0.0",

    # HTTP client
    "requests>=2.31.0",

    # Web search
    "ddgs>=9.10.0",

    # OpenAI SDK directly (for Whisper STT and TTS in voice feature)
    "openai>=1.0.0",
]
```

```bash
# Install all dependencies
uv sync
# or: pip install -e .
```

### Step 0.3 — Directory Structure

Create all directories and `__init__.py` files FIRST, before writing any logic.
Python needs these files to resolve imports. A missing `__init__.py` causes
`ModuleNotFoundError` that looks confusing because the file you're importing EXISTS —
the issue is Python can't treat the folder as a package.

```
voice_agent_placement/
│
├── .env                         ← API keys (never commit this)
├── .gitignore
├── pyproject.toml
├── main.py                      ← FastAPI app entry point
│
├── api/
│   ├── __init__.py
│   └── v1/
│       ├── __init__.py
│       ├── api.py               ← Router aggregator
│       └── endpoints/
│           ├── __init__.py
│           ├── chat.py
│           ├── pdf.py
│           ├── threads.py
│           └── voice.py         ← Added in Phase 6
│
├── core/
│   ├── __init__.py
│   ├── config.py                ← Settings / env vars
│   └── database.py              ← SQLite + checkpointer
│
├── schemas/
│   ├── __init__.py
│   ├── chat.py
│   ├── pdf.py
│   ├── thread.py
│   └── voice.py                 ← Added in Phase 6
│
├── services/
│   ├── __init__.py
│   ├── tools.py
│   ├── rag_service.py
│   ├── agent_service.py
│   └── voice_service.py         ← Added in Phase 6
│
├── models/
│   └── __init__.py              ← Empty for now, used for ORM models later
│
└── tests/                       ← Empty for now
```

```bash
# Create all directories and __init__.py files at once (Windows PowerShell)
$dirs = @("api","api\v1","api\v1\endpoints","core","schemas","services","models","tests")
foreach ($d in $dirs) {
    New-Item -ItemType Directory -Path $d -Force
    New-Item -ItemType File -Path "$d\__init__.py" -Force
}
```

### Step 0.4 — Environment File

```bash
# .env  — create this file manually, never via code
OPENAI_API_KEY=sk-proj-your-actual-key-here
ALPHA_VANTAGE_API_KEY=C9PE94QUEW9VWGFM
```

**Critical rules for `.env`:**
- No spaces around `=`
- No quotes around values
- `"sk-proj-..."` is wrong — the quotes become part of the string
- `sk-proj-...` is correct
- Always add `.env` to `.gitignore` before your first git commit

```bash
# .gitignore
__pycache__/
*.py[oc]
.venv/
.env
.env.*
chatbot.db
build/
dist/
```

---

## Phase 1 — FastAPI Foundations

Read this section before writing any code. These concepts are used in every phase.
Understanding them now prevents confusion later.

### 1.1 What FastAPI Actually Is

FastAPI is built on three layers:

```
Your code (route handlers, business logic)
     ↓
FastAPI  — routing, dependency injection, OpenAPI generation
     ↓
Starlette — async HTTP framework (handles the actual TCP/request/response)
     ↓
Uvicorn — ASGI server (runs the async event loop, talks to the OS)
```

When you run `uvicorn main:app`, Uvicorn starts an event loop, Starlette handles
incoming HTTP connections, FastAPI routes them to your functions, and Pydantic
validates the data going in and out.

**ASGI vs WSGI:** Traditional Python web frameworks (Flask, Django) use WSGI — they
handle one request at a time per worker. FastAPI uses ASGI — it can handle thousands
of concurrent requests in a single process using Python's `async/await`. This is why
FastAPI endpoints are declared `async def` instead of just `def`.

### 1.2 The 5-Layer Architecture and Why It Exists

```
┌─────────────────────────────────────────────────────────────────┐
│ Layer 1: api/v1/endpoints/   "What does the client want?"        │
│          HTTP routes. Receives requests, returns responses.      │
│          Contains ZERO business logic.                           │
├─────────────────────────────────────────────────────────────────┤
│ Layer 2: schemas/            "Is the data valid?"                │
│          Pydantic models. Defines the shape of requests and      │
│          responses. FastAPI uses these for auto-validation.      │
├─────────────────────────────────────────────────────────────────┤
│ Layer 3: services/           "Do the actual work."               │
│          All business logic. LLM calls, RAG, tools, voice.      │
│          No knowledge of HTTP exists here.                       │
├─────────────────────────────────────────────────────────────────┤
│ Layer 4: core/               "What are the settings?"            │
│          Configuration and shared infrastructure.                │
│          Everything reads from here. Nothing writes to here.     │
├─────────────────────────────────────────────────────────────────┤
│ Layer 5: models/             "What is the database shape?"       │
│          ORM models for database tables.                         │
│          (Empty now, used when you add SQLAlchemy)               │
└─────────────────────────────────────────────────────────────────┘
```

**The cardinal rule: imports only flow downward.**

```
endpoints → services → core
endpoints → schemas
services  → core
services  → models
```

A service never imports from an endpoint. Core never imports from services.
If you break this rule, you have rebuilt the monolith with more files.

### 1.3 Dependency Injection — The Most Important FastAPI Concept

Dependency Injection (DI) means that instead of a function creating the objects it needs,
those objects are provided to it from outside. FastAPI has a built-in DI system using `Depends`.

**Without DI (tightly coupled, hard to test):**
```python
@router.post("/chat")
async def chat(body: ChatRequest):
    # Creating the service INSIDE the handler — bad
    # You cannot swap this out for a mock in tests
    service = AgentService()
    return service.invoke(body.message)
```

**With DI (loosely coupled, easy to test):**
```python
def get_agent_service() -> AgentService:
    return agent_service  # return the singleton

@router.post("/chat")
async def chat(
    body: ChatRequest,
    service: AgentService = Depends(get_agent_service)  # injected
):
    return service.invoke(body.message)
```

**In your project**, you use a simpler form of DI: module-level singletons.
The `agent_service = AgentService()` at the bottom of `agent_service.py` is
created once and imported by the endpoint. This achieves the same decoupling
(endpoint does not create the service) without the boilerplate of `Depends`.

The full `Depends` pattern becomes essential when you need:
- Database sessions that open/close per-request (SQLAlchemy)
- Authentication that validates a token before the handler runs
- Feature flags that change behaviour per-request

For this project, module-level singletons are the right call. Understand both patterns.

### 1.4 Pydantic — Automatic Validation

```python
from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    thread_id: str = Field(..., description="Unique conversation ID")
    message: str = Field(..., min_length=1)
```

When FastAPI sees `body: ChatRequest` in a route handler, it:
1. Reads the raw JSON from the request body
2. Parses it into a Python dict
3. Runs all Pydantic validators (type checking, min_length, etc.)
4. If validation fails → returns `422 Unprocessable Entity` automatically, your code never runs
5. If validation passes → gives you a typed `ChatRequest` object

You write zero validation code. The schema IS the validation.

**`Field(...)` means required.** `Field("default")` means optional with a default.
`Field(..., min_length=1)` means required AND must be at least 1 character.

### 1.5 How to Run and Test

```bash
# Run the server (from project root, venv activated)
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# --reload: auto-restart when you save a file (development only)
# --host 0.0.0.0: accessible from your network, not just localhost
# --port 8000: the port
```

Once running:
- **Swagger UI:** `http://localhost:8000/docs` — interactive API documentation, test endpoints in browser
- **ReDoc:** `http://localhost:8000/redoc` — cleaner read-only docs
- **Health check:** `http://localhost:8000/health`

The Swagger UI is generated automatically from your Pydantic schemas. Every field,
description, and example you write in your schemas appears there with zero extra work.

---

## Phase 2 — Basic Chatbot

**What we build:** A single `/chat` endpoint. No memory — every message starts fresh.
No tools — the LLM answers from its training data only.

**Concepts introduced:** config layer, service layer, schemas, endpoint structure,
the LangGraph graph with no checkpointer.

**Files to create in this phase:**
```
core/config.py
services/agent_service.py   (minimal version)
schemas/chat.py
api/v1/endpoints/chat.py
api/v1/api.py
main.py
```

### `core/config.py`

This is always the first file you write. Everything else depends on it.

```python
# core/config.py
# pydantic-settings reads your .env file and maps each variable to a typed
# Python field. If a required field is missing, the app crashes at startup
# with a clear error — better to fail fast at startup than silently at runtime.

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Required — must exist in .env, no default value
    openai_api_key: str

    # Optional — have defaults, can be overridden in .env
    model_name: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"
    sqlite_db_path: str = "../chatbot.db"
    alpha_vantage_api_key: str = "C9PE94QUEW9VWGFM"
    chunk_size: int = 1000
    chunk_overlap: int = 200
    retriever_k: int = 4
    tts_voice: str = "alloy"  # for Phase 6: alloy, echo, fable, onyx, nova, shimmer

    class Config:
        env_file = "../.env"
        env_file_encoding = "utf-8"


# Module-level singleton.
# Importing this triggers the .env read ONCE.
# Every other module does: from core.config import settings
settings = Settings()
```

### `schemas/chat.py`

```python
# schemas/chat.py
# One file per resource. This file owns the chat resource's data contracts.
# FastAPI reads these at startup to build the OpenAPI spec and /docs UI.

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    thread_id: str = Field(..., description="Unique conversation ID — links messages into a conversation")
    message: str = Field(..., min_length=1, description="The user's message text")


class ChatResponse(BaseModel):
    thread_id: str
    reply: str
```

### `services/agent_service.py` — Phase 2 version (no persistence, no tools)

```python
# services/agent_service.py  [PHASE 2 — minimal version]
# In this phase: just an LLM call. No tools, no memory.
# We will add to this file in phases 3, 4, and 5.

from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import START, StateGraph
from langgraph.graph.message import add_messages

from core.config import settings


class ChatState(TypedDict):
    # add_messages reducer: new messages are APPENDED to the list, never replace it.
    # This is what gives LangGraph its memory within a single run.
    messages: Annotated[list[BaseMessage], add_messages]


class AgentService:

    def __init__(self):
        self._llm = ChatOpenAI(
            model=settings.model_name,
            api_key=settings.openai_api_key,
        )
        self._graph = self._build_graph()

    def _build_graph(self):
        """
        Minimal graph — just one node that calls the LLM.
        No tools, no checkpointer, no loops.

        Flow:  START → chat_node → END
        """

        def chat_node(state: ChatState, config=None):
            system = SystemMessage(content="You are a helpful AI assistant.")
            response = self._llm.invoke([system, *state["messages"]])
            return {"messages": [response]}

        graph = StateGraph(ChatState)
        graph.add_node("chat_node", chat_node)
        graph.add_edge(START, "chat_node")

        # No checkpointer in Phase 2 — no memory between requests
        return graph.compile()

    def invoke(self, message: str, thread_id: str) -> str:
        result = self._graph.invoke(
            {"messages": [HumanMessage(content=message)]}
        )
        return result["messages"][-1].content


# Singleton — created once, shared by all requests
agent_service = AgentService()
```

### `api/v1/endpoints/chat.py`

```python
# api/v1/endpoints/chat.py
# The endpoint's only jobs:
#   1. Receive the validated request (FastAPI + Pydantic handle validation)
#   2. Call the service
#   3. Return the response
#   4. Catch exceptions and convert to HTTPException
# No business logic lives here.

from fastapi import APIRouter, HTTPException

from schemas.chat import ChatRequest, ChatResponse
from services.agent_service import agent_service

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/", response_model=ChatResponse)
async def chat(body: ChatRequest):
    """Send a message to the AI agent."""
    try:
        reply = agent_service.invoke(message=body.message, thread_id=body.thread_id)
        return ChatResponse(thread_id=body.thread_id, reply=reply)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### `api/v1/api.py`

```python
# api/v1/api.py
# The router aggregator. All endpoint routers are included here.
# This file is the only place that knows about all routes.
# Adding a new feature = adding one include_router() line here.

from fastapi import APIRouter

from api.v1.endpoints import chat

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(chat.router)      # → /api/v1/chat/
# Phase 4: api_router.include_router(threads.router)
# Phase 5: api_router.include_router(pdf.router)
# Phase 6: api_router.include_router(voice.router)
```

### `main.py`

```python
# main.py
# The FastAPI application entry point.
# This file stays small. Its only jobs:
#   1. Create the app
#   2. Register the router
#   3. Define startup/shutdown logic (lifespan)
#   4. Define global endpoints (health check)

from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.v1.api import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan replaces the old @app.on_event("startup") pattern.
    Code before `yield` runs on startup (before first request).
    Code after `yield` runs on shutdown (after last request).

    Our services are module-level singletons, so they initialise
    automatically when Python imports them. The lifespan is where
    you'd put explicit startup tasks: health-checking external APIs,
    pre-loading models, running DB migrations.
    """
    print("🚀 Starting up...")
    yield
    print("🛑 Shutting down...")


app = FastAPI(
    title="RAG AI Agent API",
    description="AI chatbot with PDF RAG, web search, stock prices, and voice",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(api_router)


@app.get("/health", tags=["system"])
async def health_check():
    """Quick liveness check — confirms the server is running."""
    return {"status": "healthy", "version": "1.0.0"}
```

### Test Phase 2

```bash
uvicorn main:app --reload
```

Open `http://localhost:8000/docs`. You should see one endpoint: `POST /api/v1/chat/`.

Try it:
```json
{
  "thread_id": "test-1",
  "message": "What is the capital of France?"
}
```

Expected response:
```json
{
  "thread_id": "test-1",
  "reply": "The capital of France is Paris."
}
```

Send the same `thread_id` again with "What did I just ask you?" — you will get a wrong answer
because there is no memory yet. That is Phase 3's job.

---

## Phase 3 — Adding Persistence (Conversation Memory)

**What we add:** SQLite checkpointer. Each `thread_id` now has its full message history
saved to disk. Every request for the same thread loads the previous conversation.

**Concepts introduced:** LangGraph checkpointing, SQLite, the `config` dict pattern.

**New file:** `core/database.py`
**Modified file:** `services/agent_service.py`

### `core/database.py`

```python
# core/database.py
# The SQLite connection and LangGraph checkpointer live here as module-level singletons.
# One connection, shared across all requests.
#
# Why check_same_thread=False?
# SQLite's Python binding defaults to only allowing access from the thread that created
# the connection. FastAPI uses multiple threads. This flag disables that restriction.
# For production scale, use PostgreSQL with async SQLAlchemy instead of SQLite.

import sqlite3

from langgraph.checkpoint.sqlite import SqliteSaver

from core.config import settings

# Created once when this module is first imported
_conn = sqlite3.connect(
    database=settings.sqlite_db_path,
    check_same_thread=False,
)

# checkpointer wraps the connection with LangGraph's save/load interface
checkpointer = SqliteSaver(conn=_conn)


def get_checkpointer() -> SqliteSaver:
    """
    Dependency injection factory.
    Currently returns the module singleton.
    If you swap to PostgreSQL later, only this function changes.
    """
    return checkpointer
```

### Update `services/agent_service.py` for Phase 3

Changes: import checkpointer, pass it to `graph.compile()`, use `config` in invoke.

```python
# services/agent_service.py  [PHASE 3 — adds persistence]

from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import START, StateGraph
from langgraph.graph.message import add_messages

from core.config import settings
from core.database import checkpointer   # ← NEW: import checkpointer


class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


class AgentService:

    def __init__(self):
        self._llm = ChatOpenAI(
            model=settings.model_name,
            api_key=settings.openai_api_key,
        )
        self._graph = self._build_graph()

    def _build_graph(self):

        def chat_node(state: ChatState, config=None):
            system = SystemMessage(content="You are a helpful AI assistant.")
            response = self._llm.invoke([system, *state["messages"]])
            return {"messages": [response]}

        graph = StateGraph(ChatState)
        graph.add_node("chat_node", chat_node)
        graph.add_edge(START, "chat_node")

        # ← NEW: passing checkpointer enables persistent memory
        # LangGraph will save state to SQLite after every node execution
        return graph.compile(checkpointer=checkpointer)

    def invoke(self, message: str, thread_id: str) -> str:
        # ← NEW: the config dict is the key to memory.
        # LangGraph uses thread_id to find and load the right conversation
        # from SQLite before running the graph.
        config = {"configurable": {"thread_id": thread_id}}

        result = self._graph.invoke(
            {"messages": [HumanMessage(content=message)]},
            config=config,       # ← pass config here
        )
        return result["messages"][-1].content

    def get_all_threads(self) -> list[str]:
        """List all thread IDs that have saved checkpoints."""
        threads = set()
        for checkpoint in checkpointer.list(None):
            threads.add(checkpoint.config["configurable"]["thread_id"])
        return list(threads)


agent_service = AgentService()
```

### Test Phase 3

Send two messages with the same `thread_id`:

**Message 1:**
```json
{"thread_id": "memory-test", "message": "My favourite colour is blue."}
```

**Message 2:**
```json
{"thread_id": "memory-test", "message": "What is my favourite colour?"}
```

The agent should now answer "Blue" — it remembered. Send the same second message with a
**different** `thread_id` — it should not know. That is isolation working correctly.

A `chatbot.db` file will have appeared in your project root. This is the SQLite database
that holds all conversation state. It's in `.gitignore` — it's a runtime artefact, not code.

**What is actually happening under the hood:**

Every time `graph.invoke(state, config)` is called, LangGraph:
1. Reads the latest checkpoint for `thread_id` from SQLite
2. Merges the stored messages with the new incoming message
3. Runs the graph nodes
4. Saves the updated state back to SQLite

The `add_messages` reducer is what makes step 2 work correctly — it appends new messages
to the loaded history rather than replacing it.

---

## Phase 4 — Adding Agentic Tools

**What we add:** Three tools (calculator, stock price, web search) + the thread listing
endpoint. The LLM can now decide to call external APIs before answering.

**Concepts introduced:** LangChain `@tool` decorator, `bind_tools`, `ToolNode`,
`tools_condition`, the agent loop, `tools_condition` routing.

**New files:** `services/tools.py`, `schemas/thread.py`, `api/v1/endpoints/threads.py`
**Modified files:** `services/agent_service.py`, `api/v1/api.py`

### Why Tools Matter — The Agent Loop

Without tools, the LLM can only answer from its training data. With tools, the graph
becomes cyclical:

```
START → chat_node
            ↓
      [LLM decides]
      /            \
  "I need data"    "I can answer directly"
      ↓                      ↓
  tools node              END
      ↓
  tool executes
      ↓
  chat_node  (loops back — LLM now has tool result)
      ↓
  "Now I can answer"
      ↓
  END
```

The LLM might call multiple tools before answering. This loop is the core of what makes
it an "agent" rather than a simple "chain".

### `services/tools.py`

```python
# services/tools.py
# Stateless tools the LLM agent can call.
# "Stateless" means they don't depend on which user or thread is calling them.
# They just do their job with the arguments the LLM passes.
#
# The @tool decorator does two things:
#   1. Reads the function's TYPE ANNOTATIONS to build a JSON schema the LLM understands
#   2. Reads the DOCSTRING to tell the LLM when and why to call this tool
# Both are critical. A missing docstring = LLM doesn't know when to use the tool.
# Missing type annotations = LLM doesn't know what arguments to pass.

import requests
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.tools import tool

from core.config import settings

# Pre-built LangChain tool — wraps DuckDuckGo search API
# Stateless and safe to share across all threads
search_tool = DuckDuckGoSearchRun(region="us-en")


@tool
def calculator(first_num: float, second_num: float, operation: str) -> dict:
    """
    Perform basic arithmetic on two numbers.
    Supported operations: add, sub, mul, div
    Use this for any mathematical calculation the user asks for.
    """
    try:
        if operation == "add":
            result = first_num + second_num
        elif operation == "sub":
            result = first_num - second_num
        elif operation == "mul":
            result = first_num * second_num
        elif operation == "div":
            if second_num == 0:
                return {"error": "Division by zero is not allowed"}
            result = first_num / second_num
        else:
            return {"error": f"Unsupported operation '{operation}'. Use: add, sub, mul, div"}

        return {
            "first_num": first_num,
            "second_num": second_num,
            "operation": operation,
            "result": result,
        }
    except Exception as e:
        return {"error": str(e)}


@tool
def get_stock_price(symbol: str) -> dict:
    """
    Fetch the latest stock price for a given ticker symbol.
    Examples: 'AAPL' for Apple, 'TSLA' for Tesla, 'GOOGL' for Google.
    Use this when the user asks about a stock price or company valuation.
    """
    url = (
        "https://www.alphavantage.co/query"
        f"?function=GLOBAL_QUOTE&symbol={symbol}"
        f"&apikey={settings.alpha_vantage_api_key}"
    )
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e)}
```

### `schemas/thread.py`

```python
# schemas/thread.py
from pydantic import BaseModel
from typing import Optional


class ThreadInfo(BaseModel):
    thread_id: str
    has_document: bool
    document_filename: Optional[str] = None
    document_chunks: Optional[int] = None
```

### `api/v1/endpoints/threads.py`

```python
# api/v1/endpoints/threads.py
from fastapi import APIRouter

from schemas.thread import ThreadInfo
from services.agent_service import agent_service
from services.rag_service import rag_service      # added in Phase 5, import now

router = APIRouter(prefix="/threads", tags=["threads"])


@router.get("/", response_model=list[str])
async def list_threads():
    """Returns all thread IDs that have saved conversation history in the database."""
    return agent_service.get_all_threads()


@router.get("/{thread_id}", response_model=ThreadInfo)
async def get_thread_info(thread_id: str):
    """Returns metadata for a specific thread — including whether a PDF was uploaded."""
    meta = rag_service.get_metadata(thread_id)
    return ThreadInfo(
        thread_id=thread_id,
        has_document=rag_service.has_document(thread_id),
        document_filename=meta.get("filename"),
        document_chunks=meta.get("chunks"),
    )
```

### Update `services/agent_service.py` for Phase 4

```python
# services/agent_service.py  [PHASE 4 — adds tools and agent loop]

from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition   # ← NEW

from core.config import settings
from core.database import checkpointer
from services.tools import calculator, get_stock_price, search_tool  # ← NEW


class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


class AgentService:

    def __init__(self):
        self._llm = ChatOpenAI(model=settings.model_name, api_key=settings.openai_api_key)
        self._graph = self._build_graph()

    def _build_graph(self):
        """
        Phase 4 graph — adds tools and conditional routing.

        tools_condition is a pre-built LangGraph function that checks the last message:
          - If it has tool_calls → route to "tools" node
          - If it has no tool_calls → route to END

        This creates the agent loop: LLM calls tool → tool runs → LLM sees result → LLM answers
        """
        base_tools = [search_tool, calculator, get_stock_price]

        # bind_tools tells the LLM what tools exist (sends schemas to OpenAI function-calling)
        llm_with_tools = self._llm.bind_tools(base_tools)

        # ToolNode is a pre-built node that executes whatever tool the LLM requested
        # It needs the EXACT same tool list as bind_tools — a mismatch = "Tool not found" crash
        tool_node = ToolNode(base_tools)

        def chat_node(state: ChatState, config=None):
            thread_id = config.get("configurable", {}).get("thread_id", "") if config else ""

            system = SystemMessage(content=(
                "You are a helpful AI assistant.\n"
                "Available tools:\n"
                "  • search_tool — search the web for current information\n"
                "  • calculator — perform arithmetic (add, sub, mul, div)\n"
                "  • get_stock_price — fetch live stock prices by ticker symbol\n"
            ))
            response = llm_with_tools.invoke([system, *state["messages"]], config=config)
            return {"messages": [response]}

        graph = StateGraph(ChatState)
        graph.add_node("chat_node", chat_node)
        graph.add_node("tools", tool_node)
        graph.add_edge(START, "chat_node")
        graph.add_conditional_edges("chat_node", tools_condition)  # ← branching
        graph.add_edge("tools", "chat_node")                       # ← the loop back

        return graph.compile(checkpointer=checkpointer)

    def invoke(self, message: str, thread_id: str) -> str:
        config = {"configurable": {"thread_id": thread_id}}
        result = self._graph.invoke(
            {"messages": [HumanMessage(content=message)]},
            config=config,
        )
        return result["messages"][-1].content

    def get_all_threads(self) -> list[str]:
        threads = set()
        for checkpoint in checkpointer.list(None):
            threads.add(checkpoint.config["configurable"]["thread_id"])
        return list(threads)


agent_service = AgentService()
```

### Update `api/v1/api.py` for Phase 4

```python
# api/v1/api.py
from fastapi import APIRouter
from api.v1.endpoints import chat, threads   # ← add threads

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(chat.router)
api_router.include_router(threads.router)    # ← add this line
```

### Test Phase 4

```json
{"thread_id": "tools-test", "message": "What is 847 multiplied by 23?"}
```
The agent should use the calculator and return `19481`.

```json
{"thread_id": "tools-test", "message": "What is the current price of AAPL?"}
```
The agent should call `get_stock_price` and return a real price.

```
GET /api/v1/threads/
```
Should return `["tools-test"]` (and any other threads from Phase 3 tests).

---

## Phase 5 — Adding RAG (PDF Knowledge)

**What we add:** PDF upload endpoint, FAISS vector store per thread, `rag_tool` for
the agent. After uploading a PDF, the agent can answer questions about its content.

**Concepts introduced:** Embeddings, vector similarity search, FAISS, chunking,
the closure pattern for per-thread tools, `ToolNode` compile-time vs call-time resolution.

**New files:** `services/rag_service.py`, `schemas/pdf.py`, `api/v1/endpoints/pdf.py`
**Modified files:** `services/agent_service.py`, `api/v1/api.py`

### How RAG Works

```
UPLOAD phase (happens once):
  PDF file bytes
    → write to temp file
    → PyPDFLoader → list of pages (Document objects)
    → RecursiveCharacterTextSplitter → overlapping chunks of ~1000 chars
    → OpenAIEmbeddings → each chunk becomes a vector (list of 1536 floats)
    → FAISS.from_documents → builds an in-memory index of all vectors
    → stored in _THREAD_RETRIEVERS[thread_id]

QUERY phase (happens on each chat message):
  user question
    → embed the question using same model
    → FAISS similarity search → find top-k most similar chunks
    → return chunk text as context
    → LLM reads context + question → generates answer
```

**Why chunk overlap:** If a key sentence spans the boundary between two chunks,
without overlap neither chunk contains it fully. With `chunk_overlap=200`, consecutive
chunks share 200 characters, ensuring no sentence is split across chunks.

### `schemas/pdf.py`

```python
# schemas/pdf.py
from pydantic import BaseModel


class PDFUploadResponse(BaseModel):
    thread_id: str
    filename: str
    documents: int      # number of PDF pages loaded
    chunks: int         # number of chunks after splitting
    message: str
```

### `services/rag_service.py`

```python
# services/rag_service.py
# Manages in-memory FAISS vector stores, one per thread.
#
# Important limitation: these stores live in RAM.
# Server restart = all uploaded PDFs are gone.
# Production upgrade path: swap FAISS for ChromaDB (local persistence)
# or Pinecone/Weaviate (cloud). The interface (retriever.invoke) stays the same.

import os
import tempfile
from typing import Optional

from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from core.config import settings

# ---------------------------------------------------------------------------
# Module-level stores — survive for the lifetime of the running process
# ---------------------------------------------------------------------------
_THREAD_RETRIEVERS: dict = {}   # thread_id → FAISS retriever
_THREAD_METADATA: dict = {}     # thread_id → {filename, documents, chunks}

# One embeddings client, created once, reused for every PDF upload
# Creating it here (module level) means we don't recreate it per request
_embeddings = OpenAIEmbeddings(
    model=settings.embedding_model,
    api_key=settings.openai_api_key,
)


class RAGService:

    def ingest_pdf(self, file_bytes: bytes, thread_id: str, filename: Optional[str] = None) -> dict:
        """
        Full ingestion pipeline. Returns metadata dict.
        PyPDFLoader requires a real file path (not raw bytes), so we write
        to a temp file first, then delete it after FAISS has its copy.
        """
        if not file_bytes:
            raise ValueError("Empty file bytes — nothing to ingest.")

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as f:
            f.write(file_bytes)
            temp_path = f.name

        try:
            # 1. Load PDF pages
            loader = PyPDFLoader(temp_path)
            docs = loader.load()

            # 2. Split into overlapping chunks
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=settings.chunk_size,
                chunk_overlap=settings.chunk_overlap,
                separators=["\n\n", "\n", " ", ""],
            )
            chunks = splitter.split_documents(docs)

            # 3. Embed and build FAISS index
            vector_store = FAISS.from_documents(chunks, _embeddings)

            # 4. Wrap as retriever (similarity search, return top-k chunks)
            retriever = vector_store.as_retriever(
                search_type="similarity",
                search_kwargs={"k": settings.retriever_k},
            )
            _THREAD_RETRIEVERS[str(thread_id)] = retriever

            metadata = {
                "filename": filename or os.path.basename(temp_path),
                "documents": len(docs),
                "chunks": len(chunks),
            }
            _THREAD_METADATA[str(thread_id)] = metadata
            return metadata

        finally:
            try:
                os.remove(temp_path)   # FAISS keeps its own copy in memory
            except OSError:
                pass

    def get_retriever(self, thread_id: str):
        return _THREAD_RETRIEVERS.get(str(thread_id))

    def has_document(self, thread_id: str) -> bool:
        return str(thread_id) in _THREAD_RETRIEVERS

    def get_metadata(self, thread_id: str) -> dict:
        return _THREAD_METADATA.get(str(thread_id), {})


rag_service = RAGService()
```

### `api/v1/endpoints/pdf.py`

```python
# api/v1/endpoints/pdf.py
# Why Query() and not Form() for thread_id?
# When a route uses File(), the request body must be multipart/form-data.
# If you also use Form() for a text field, the client must send that text field
# as a multipart text part — most clients do this wrong, causing a 422.
# Using Query() puts thread_id in the URL (?thread_id=abc), which every client handles.

from fastapi import APIRouter, File, HTTPException, Query, UploadFile

from schemas.pdf import PDFUploadResponse
from services.rag_service import rag_service

router = APIRouter(prefix="/pdf", tags=["pdf"])


@router.post("/upload", response_model=PDFUploadResponse)
async def upload_pdf(
    thread_id: str = Query(..., description="Thread ID to attach this PDF to"),
    file: UploadFile = File(...),
):
    """
    Upload a PDF for a thread.
    Call: POST /api/v1/pdf/upload?thread_id=my-thread
    Body: multipart/form-data, key='file', value=the PDF
    """
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files accepted.")

    file_bytes = await file.read()
    try:
        metadata = rag_service.ingest_pdf(
            file_bytes=file_bytes,
            thread_id=thread_id,
            filename=file.filename,
        )
        return PDFUploadResponse(
            thread_id=thread_id,
            message="PDF processed successfully.",
            **metadata,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### Update `services/agent_service.py` for Phase 5

The key design problem: `rag_tool` needs to know the `thread_id` at call time (to look up
the right FAISS retriever), but `ToolNode` needs to know about it at compile time.

**The solution:** Define `rag_tool` inside `_build_graph()` as a closure. It does a live
lookup of `rag_service.get_retriever(thread_id)` when called — so it always gets the right
retriever. But it is defined and registered in `ToolNode` at compile time — so the graph
doesn't crash.

```python
# services/agent_service.py  [PHASE 5 — final version with RAG]

from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

from core.config import settings
from core.database import checkpointer
from services.rag_service import rag_service
from services.tools import calculator, get_stock_price, search_tool


class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


class AgentService:

    def __init__(self):
        self._llm = ChatOpenAI(model=settings.model_name, api_key=settings.openai_api_key)
        self._graph = self._build_graph()

    def _build_graph(self):
        # rag_tool is defined HERE so ToolNode knows about it at compile time,
        # but it resolves the retriever at CALL time using the thread_id argument.
        # This is the closure pattern: the function captures rag_service from scope,
        # then uses the runtime thread_id argument to find the right retriever.
        @tool
        def rag_tool(query: str, thread_id: str = "") -> dict:
            """
            Retrieve relevant passages from the PDF document uploaded for this thread.
            Always pass the current thread_id when calling this tool.
            Use this for any question about the content of an uploaded document.
            """
            retriever = rag_service.get_retriever(thread_id)
            if retriever is None:
                return {
                    "error": f"No PDF uploaded for thread '{thread_id}'. "
                             "Ask the user to upload a document first."
                }
            results = retriever.invoke(query)
            return {
                "query": query,
                "context": [doc.page_content for doc in results],
                "metadata": [doc.metadata for doc in results],
                "source_file": rag_service.get_metadata(thread_id).get("filename"),
            }

        # CRITICAL: rag_tool must be in BOTH bind_tools AND ToolNode
        # bind_tools → LLM knows it can call rag_tool
        # ToolNode   → graph can execute rag_tool when LLM calls it
        # A mismatch between these two lists = "Tool not found" crash at runtime
        all_tools = [search_tool, calculator, get_stock_price, rag_tool]
        llm_with_tools = self._llm.bind_tools(all_tools)
        tool_node = ToolNode(all_tools)

        def chat_node(state: ChatState, config=None):
            thread_id = config.get("configurable", {}).get("thread_id", "") if config else ""
            has_doc = rag_service.has_document(thread_id)

            doc_hint = (
                f"A PDF is available for thread '{thread_id}'. "
                "Use rag_tool with thread_id when the user asks about it."
                if has_doc else "No PDF uploaded for this thread yet."
            )

            system = SystemMessage(content=(
                "You are a helpful AI assistant.\n\n"
                f"Thread context: {doc_hint}\n\n"
                "Available tools:\n"
                f"  • rag_tool — answer questions about the uploaded PDF (thread_id='{thread_id}')\n"
                "  • search_tool — search the web\n"
                "  • calculator — arithmetic\n"
                "  • get_stock_price — live stock prices\n\n"
                "Always pass the thread_id argument when calling rag_tool."
            ))
            response = llm_with_tools.invoke([system, *state["messages"]], config=config)
            return {"messages": [response]}

        graph = StateGraph(ChatState)
        graph.add_node("chat_node", chat_node)
        graph.add_node("tools", tool_node)
        graph.add_edge(START, "chat_node")
        graph.add_conditional_edges("chat_node", tools_condition)
        graph.add_edge("tools", "chat_node")

        return graph.compile(checkpointer=checkpointer)

    def invoke(self, message: str, thread_id: str) -> str:
        config = {"configurable": {"thread_id": thread_id}}
        result = self._graph.invoke(
            {"messages": [HumanMessage(content=message)]},
            config=config,
        )
        return result["messages"][-1].content

    def get_all_threads(self) -> list[str]:
        threads = set()
        for checkpoint in checkpointer.list(None):
            threads.add(checkpoint.config["configurable"]["thread_id"])
        return list(threads)


agent_service = AgentService()
```

### Update `api/v1/api.py` for Phase 5

```python
from fastapi import APIRouter
from api.v1.endpoints import chat, pdf, threads

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(chat.router)
api_router.include_router(threads.router)
api_router.include_router(pdf.router)      # ← add this
```

### Test Phase 5

1. Upload a PDF: `POST /api/v1/pdf/upload?thread_id=doc-test` with a PDF in the body
2. Ask about it: `POST /api/v1/chat/` with `{"thread_id": "doc-test", "message": "summarise this document"}`
3. Check thread info: `GET /api/v1/threads/doc-test` — `has_document` should be `true`

---

## Phase 6 — Adding Voice Interface

**What we add:** A voice chat endpoint. The user speaks, the agent listens (Whisper STT),
thinks (same LangGraph agent), and speaks back (OpenAI TTS).

**Concepts introduced:** `StreamingResponse`, binary file responses, OpenAI audio APIs,
how to add a completely new feature without touching any existing code.

**New files:** `services/voice_service.py`, `schemas/voice.py`, `api/v1/endpoints/voice.py`
**Modified files:** `api/v1/api.py` (one line added)

**The key architectural insight:** The voice endpoint calls `agent_service.invoke()` —
the exact same method that the text chat endpoint calls. The voice layer is just a
wrapper that converts audio → text → audio around the existing agent. The agent doesn't
know or care whether the input came from typing or speaking.

```
TEXT CHAT:  client types  →  POST /api/v1/chat/        →  agent  →  JSON reply
VOICE CHAT: client speaks →  POST /api/v1/voice/chat/  →  [STT]
                                                             ↓
                                                           agent (SAME agent_service.invoke())
                                                             ↓
                                                           [TTS]  →  MP3 audio bytes
```

> **Two production bugs were found and fixed during development of this endpoint.
> Both are documented in detail in the Bugs Encountered section at the end of Phase 6.**

### `schemas/voice.py`

```python
# schemas/voice.py
# The voice endpoint returns audio bytes (StreamingResponse), not JSON.
# So we don't use a response_model= on the endpoint.
# VoiceChatMetadata documents the data for reference and for a
# potential /voice/transcript endpoint (text-only response from a voice input).

from pydantic import BaseModel


class VoiceChatMetadata(BaseModel):
    """
    Metadata about a voice chat exchange.
    Not used as a FastAPI response_model (we stream binary audio),
    but useful as documentation and for testing.
    """
    thread_id: str
    transcript: str     # what Whisper heard from the user's audio
    reply_text: str     # what the agent said (text form)
```

### `services/voice_service.py`

```python
# services/voice_service.py
# Two responsibilities:
#   1. transcribe(audio_bytes) → text   (Speech-to-Text via OpenAI Whisper)
#   2. synthesise(text) → audio_bytes   (Text-to-Speech via OpenAI TTS)
#
# Both use the OpenAI SDK directly (not LangChain) because these are
# audio APIs, not LLM APIs.
#
# Supported input formats for Whisper: mp3, mp4, mpeg, mpga, m4a, wav, webm
# Output format from TTS: mp3

import io

from openai import OpenAI

from core.config import settings


class VoiceService:

    def __init__(self):
        # OpenAI client — same API key as the LLM, different API endpoints
        # Creating it once here means we don't create a new HTTP client per request
        self._client = OpenAI(api_key=settings.openai_api_key)

    def transcribe(self, audio_bytes: bytes, filename: str = "audio.mp3") -> str:
        """
        Convert audio bytes to text using OpenAI Whisper.

        Why BytesIO + .name?
        The OpenAI SDK expects a file-like object with a name attribute.
        BytesIO wraps raw bytes as a file-like object in memory.
        The .name tells Whisper which format decoder to use (mp3, wav, etc.).
        We never write to disk — everything stays in RAM.

        Returns the transcribed text string.
        Raises an exception (caught by the endpoint) on API failure.
        """
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = filename  # Whisper needs this to detect audio format

        result = self._client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            response_format="text",  # return a plain string, not a JSON object
        )
        return result

    def synthesise(self, text: str) -> bytes:
        """
        Convert text to MP3 audio bytes using OpenAI TTS.

        model options:
          tts-1      — faster, slightly lower quality, better for real-time
          tts-1-hd   — higher quality, slightly slower

        voice options (set in .env as TTS_VOICE):
          alloy, echo, fable, onyx, nova, shimmer
          Each has a different character. 'alloy' is neutral and clear.

        Returns raw MP3 bytes ready to stream to the client.
        """
        response = self._client.audio.speech.create(
            model="tts-1",
            voice=settings.tts_voice,
            input=text,
        )
        return response.content  # raw MP3 bytes


# Singleton — imported by the voice endpoint
voice_service = VoiceService()
```

### `api/v1/endpoints/voice.py`

Two bugs were discovered and fixed when testing this endpoint live. Both are explained
in detail in the **Bugs Encountered** section directly below the code.

```python
# api/v1/endpoints/voice.py
# Voice chat endpoint — audio in, audio out.
# Internally identical to the text chat endpoint: same agent, same thread memory.
#
# Why Response and NOT StreamingResponse?
# StreamingResponse iterates over a BytesIO object line-by-line, splitting on \n (0x0A).
# MP3 is raw binary — it contains 0x0A bytes throughout as part of the audio data.
# Splitting on those corrupts the file. Response(content=bytes) sends the full buffer
# in one shot with no processing. Since TTS returns all bytes synchronously, there is
# no benefit to streaming anyway.
#
# Why no response_model=?
# response_model is for JSON responses only. For binary responses (audio, images, files),
# return a Response subclass directly and omit response_model.

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi.responses import Response

from services.agent_service import agent_service
from services.voice_service import voice_service

router = APIRouter(prefix="/voice", tags=["voice"])


def _safe_header(value: str, max_len: int = 500) -> str:
    """
    Sanitize a string for use as an HTTP header value.

    HTTP headers cannot contain newlines (\n, \r\n) or carriage returns.
    They are protocol delimiters in HTTP/1.1 — a \n inside a header value
    would be interpreted as the start of a new header line, which is a
    security vulnerability known as HTTP Header Injection.

    Uvicorn correctly rejects such values with:
        RuntimeError: Invalid HTTP header value

    LLM replies almost always contain newlines (bullet points, numbered lists,
    paragraphs). Without this sanitization, any structured reply crashes the
    entire response — even though the audio was generated successfully.

    Fix: replace all newline variants with a space before setting the header.
    Order matters: replace \r\n (Windows) first, then \n (Unix), then \r (old Mac).
    """
    return value.replace("\r\n", " ").replace("\n", " ").replace("\r", " ")[:max_len]


@router.post("/chat")
async def voice_chat(
    thread_id: str = Query(..., description="Conversation thread ID"),
    file: UploadFile = File(..., description="Audio file — mp3, wav, m4a, or webm"),
):
    """
    Voice chat endpoint.

    Full pipeline:
      1. Receive audio file from user
      2. Transcribe audio → text  (OpenAI Whisper)
      3. Send text to AI agent    (same LangGraph agent as /chat — preserves thread memory)
      4. Convert reply → audio    (OpenAI TTS)
      5. Return MP3 bytes to client as a downloadable file

    The thread_id is shared with the text /chat endpoint.
    A conversation that started over text can continue over voice and vice versa.

    Call:     POST /api/v1/voice/chat?thread_id=my-thread
    Body:     multipart/form-data, key='file', value=audio file
    Response: audio/mpeg binary download (reply.mp3)

    Custom headers (newlines stripped by _safe_header):
      X-Transcript — what Whisper heard from the user
      X-Reply-Text — the agent's reply in text form
      X-Thread-Id  — echoes the thread_id
    """
    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio file received.")

    try:
        # Step 1: Speech → Text
        transcript = voice_service.transcribe(
            audio_bytes=audio_bytes,
            filename=file.filename or "audio.mp3",
        )

        if not transcript or not transcript.strip():
            raise HTTPException(
                status_code=422,
                detail="No speech detected in the audio file.",
            )

        # Step 2: Text → Agent → Text
        # Identical call to the text /chat endpoint. Voice is transparent to the agent.
        reply_text = agent_service.invoke(message=transcript, thread_id=thread_id)

        # Step 3: Text → Audio
        audio_response_bytes = voice_service.synthesise(text=reply_text)

        # Step 4: Return MP3 bytes.
        # Using Response (not StreamingResponse) — see file-level comment for why.
        # Content-Disposition: attachment forces a download prompt in browsers and
        # shows a download link in Swagger UI. 'inline' would try to play in-page,
        # but Swagger has no audio player so nothing would happen.
        return Response(
            content=audio_response_bytes,
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": "attachment; filename=reply.mp3",
                "X-Transcript": _safe_header(transcript),
                "X-Reply-Text": _safe_header(reply_text),
                "X-Thread-Id": thread_id,
                "Access-Control-Expose-Headers": "X-Transcript, X-Reply-Text, X-Thread-Id",
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Voice pipeline failed: {str(e)}")


@router.post("/transcribe-only")
async def transcribe_only(
    file: UploadFile = File(..., description="Audio file to transcribe"),
):
    """
    Transcribe audio to text only — no agent call, no TTS.
    Returns JSON with the transcribed text.
    Use this to test that Whisper can hear your audio before attempting a full voice chat.
    """
    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio file.")

    try:
        transcript = voice_service.transcribe(
            audio_bytes=audio_bytes,
            filename=file.filename or "audio.mp3",
        )
        return {"transcript": transcript}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### Bugs Encountered in Phase 6

Both bugs only appeared during live testing — neither caused startup errors.
This is why testing at each phase matters.

---

**Bug 1 — `RuntimeError: Invalid HTTP header value` (server crash on every voice request)**

Symptom: The request returned HTTP 200 but the server logged an exception and the
client received no usable response.

Root cause: The headers dict contained `reply_text[:500]` directly. HTTP/1.1 uses
`\r\n` as the delimiter between headers. A header value that contains a literal `\n`
byte breaks the protocol — the HTTP parser on the receiving side treats it as the start
of a new header line. This is a security vulnerability called HTTP Header Injection.
Uvicorn correctly refuses to send it and raises `RuntimeError`.

The LLM almost always returns multi-line replies (numbered steps, bullet points,
paragraphs). The first request with a structured answer crashed the server.

Fix: the `_safe_header()` function replaces all newline variants with spaces before
the value is placed into a header:
```python
def _safe_header(value: str, max_len: int = 500) -> str:
    return value.replace("\r\n", " ").replace("\n", " ").replace("\r", " ")[:max_len]
```
Note: `\r\n` must be replaced first (Windows line endings are two characters). If you
replace `\n` first, you leave lone `\r` characters behind which are still illegal.

---

**Bug 2 — Audio file downloaded but could not be played (corrupted MP3)**

Symptom: After fixing Bug 1, the file downloaded successfully but every audio player
rejected it as an invalid or corrupt file.

Root cause: `StreamingResponse` with a `BytesIO` object. Starlette's `StreamingResponse`
iteratesd over file-like objects the same way Python iterates over text files — it
yields chunks split on `\n` bytes (byte value `0x0A`). MP3 is raw binary audio data.
The `0x0A` byte appears throughout MP3 files as part of the audio encoding — it is not
a line separator. Splitting the binary stream on those bytes corrupts the MP3 frame
structure. The client receives the pieces but they cannot be reassembled into valid audio.

Fix: replace `StreamingResponse` with `Response`. `Response(content=bytes)` sends the
entire byte buffer in a single write with no iteration and no processing:
```python
# BROKEN
return StreamingResponse(content=io.BytesIO(audio_bytes), media_type="audio/mpeg", ...)

# FIXED
return Response(content=audio_bytes, media_type="audio/mpeg", ...)
```
`StreamingResponse` is the right tool when you are generating data incrementally (e.g.,
streaming a large file from disk chunk-by-chunk). When you already have all bytes in
memory — which TTS always gives you — `Response` is both correct and simpler.

Additionally, `Content-Disposition` was changed from `inline` to `attachment`:
- `inline` — tells the browser to try to render/play the file in-page. Swagger UI has
  no audio player, so nothing happens and there is no download link.
- `attachment; filename=reply.mp3` — forces every client to treat it as a file download,
  which shows a **Download file** link in Swagger UI and a save dialog in browsers.

### Update `api/v1/api.py` for Phase 6

```python
# api/v1/api.py  — FINAL VERSION
from fastapi import APIRouter
from api.v1.endpoints import chat, pdf, threads, voice   # ← add voice

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(chat.router)       # POST /api/v1/chat/
api_router.include_router(threads.router)    # GET  /api/v1/threads/
api_router.include_router(pdf.router)        # POST /api/v1/pdf/upload
api_router.include_router(voice.router)      # POST /api/v1/voice/chat
```

### Update `core/config.py` for Phase 6

Add the `tts_voice` setting (already included in the Phase 0 config above).
If you wrote config earlier without it, add this line to the `Settings` class:

```python
tts_voice: str = "alloy"   # alloy, echo, fable, onyx, nova, shimmer
```

To use a different voice, add `TTS_VOICE=nova` to your `.env`.

### Test Phase 6

**Testing in Swagger UI:**
1. Go to `http://localhost:8000/docs`
2. First test `/voice/transcribe-only` with your audio file — verify Whisper returns
   your words correctly before testing the full pipeline
3. Find `POST /api/v1/voice/chat`
4. Enter a `thread_id` in the query parameter box
5. Upload a short `.mp3` or `.wav` of yourself speaking
6. Click Execute
7. A **Download file** link appears in the response section — click it to save `reply.mp3`
8. Open `reply.mp3` in any audio player (Windows Media Player, VLC, etc.)

**Testing with curl:**
```bash
curl -X POST "http://localhost:8000/api/v1/voice/chat?thread_id=voice-test" \
  -F "file=@your_recording.mp3" \
  --output reply.mp3

# Play the response (macOS)
afplay reply.mp3

# Check the transcript headers
curl -X POST "http://localhost:8000/api/v1/voice/chat?thread_id=voice-test" \
  -F "file=@your_recording.mp3" \
  --output reply.mp3 -D -
```

**Testing the isolated transcription endpoint:**
```bash
curl -X POST "http://localhost:8000/api/v1/voice/transcribe-only" \
  -F "file=@your_recording.mp3"
# Returns: {"transcript": "What is the capital of France?"}
```

**Verify voice and text share memory:**
1. Voice: `POST /api/v1/voice/chat?thread_id=shared` with audio saying "My name is Daksh"
2. Text: `POST /api/v1/chat/` with `{"thread_id": "shared", "message": "What is my name?"}`
3. The text response should say "Daksh" — the voice message was stored in the same thread

---

## Final State — All Endpoints

```
GET  /health                             System health check

POST /api/v1/chat/                       Text chat with the AI agent
     Body (JSON): {thread_id, message}
     Response (JSON): {thread_id, reply}

GET  /api/v1/threads/                    List all conversation thread IDs
     Response (JSON): ["thread-1", "thread-2", ...]

GET  /api/v1/threads/{thread_id}         Get info about a specific thread
     Response (JSON): {thread_id, has_document, document_filename, document_chunks}

POST /api/v1/pdf/upload                  Upload a PDF to a thread
     Query: ?thread_id=abc
     Body (multipart): file=<pdf>
     Response (JSON): {thread_id, filename, documents, chunks, message}

POST /api/v1/voice/chat                  Voice chat (audio in, audio out)
     Query: ?thread_id=abc
     Body (multipart): file=<audio>
     Response: audio/mpeg binary stream
     Headers: X-Transcript, X-Reply-Text, X-Thread-Id

POST /api/v1/voice/transcribe-only       Transcribe audio without agent (testing)
     Body (multipart): file=<audio>
     Response (JSON): {transcript}
```

---

## Final Directory Structure

```
voice_agent_placement/
│
├── .env                          OPENAI_API_KEY=sk-...
├── .gitignore                    .env, chatbot.db, .venv/, __pycache__/
├── pyproject.toml
├── main.py
│
├── api/
│   ├── __init__.py
│   └── v1/
│       ├── __init__.py
│       ├── api.py                Aggregates all routers under /api/v1
│       └── endpoints/
│           ├── __init__.py
│           ├── chat.py           POST /api/v1/chat/
│           ├── pdf.py            POST /api/v1/pdf/upload
│           ├── threads.py        GET  /api/v1/threads/
│           └── voice.py          POST /api/v1/voice/chat
│
├── core/
│   ├── __init__.py
│   ├── config.py                 pydantic-settings reads .env
│   └── database.py               SQLite connection + LangGraph checkpointer
│
├── schemas/
│   ├── __init__.py
│   ├── chat.py                   ChatRequest, ChatResponse
│   ├── pdf.py                    PDFUploadResponse
│   ├── thread.py                 ThreadInfo
│   └── voice.py                  VoiceChatMetadata
│
├── services/
│   ├── __init__.py
│   ├── tools.py                  calculator, get_stock_price, search_tool
│   ├── rag_service.py            PDF ingestion, FAISS stores
│   ├── agent_service.py          LangGraph graph, invoke()
│   └── voice_service.py          Whisper STT, OpenAI TTS
│
└── models/
    └── __init__.py               Empty — for future ORM models
```

---

## Interview Talking Points

When presenting this project, frame your explanations around these themes:

**On Architecture:**
"I used a 5-layer architecture where each layer has a single responsibility.
Endpoints handle HTTP. Schemas validate data. Services contain business logic.
Core centralises configuration. Dependencies only flow downward — a service never
imports from an endpoint. This means I can add a new interface, like voice, without
touching any existing code."

**On Dependency Injection:**
"FastAPI uses Pydantic for request validation automatically — I never write
`if request.body is None` checks. For service objects, I use module-level singletons
which are a form of DI: the endpoint receives the service via import rather than
creating it, which makes the endpoint trivially testable by swapping the singleton."

**On LangGraph:**
"LangGraph is what makes this an agent rather than a chatbot. A chatbot just calls
the LLM. An agent can decide to call tools, get results, then call more tools before
answering. The key components are: `ChatState` with the `add_messages` reducer for
conversation memory, `tools_condition` for the branching logic, and `ToolNode` for
executing tools. The SQLite checkpointer persists state between HTTP requests so
conversations survive server restarts."

**On RAG:**
"RAG solves the problem of giving an LLM knowledge it wasn't trained on. The PDF is
chunked, embedded into vectors, and stored in FAISS. When a user asks a question,
the question is embedded and the most similar chunks are retrieved and injected into
the LLM's context. The key design decision was defining `rag_tool` inside `_build_graph()`
so that `ToolNode` knows about it at compile time but it resolves the per-thread FAISS
retriever at call time."

**On Voice:**
"The voice feature is architecturally a thin wrapper around the existing text agent.
The endpoint transcribes audio with Whisper, calls the exact same `agent_service.invoke()`
that the text endpoint calls, and converts the reply to speech with OpenAI TTS. The
thread_id is shared between text and voice, so a conversation can switch modalities
seamlessly. The agent doesn't know or care whether the input came from typing or speaking."

**On Bugs Fixed:**
"Four bugs were found and fixed across the project, each teaching something concrete:

1. Form() + File() 422 — When a route uses File(), the entire request must be multipart.
   Form() text fields must also be multipart, which most HTTP clients send incorrectly.
   Fixed by moving thread_id to a Query() parameter instead.

2. ToolNode/bind_tools mismatch — The LLM knew about rag_tool (via bind_tools) but
   ToolNode didn't (it was only given base_tools). Fixed by defining rag_tool inside
   _build_graph() and passing the same all_tools list to both bind_tools and ToolNode.

3. Invalid HTTP header value — LLM replies contain newlines. Putting reply_text directly
   into an HTTP header crashes uvicorn because newlines are protocol delimiters in HTTP/1.1.
   Fixed with a _safe_header() sanitizer that replaces all newline variants with spaces.

4. Corrupted MP3 audio — StreamingResponse iterates over BytesIO splitting on 0x0A
   bytes. MP3 is binary — 0x0A appears throughout as audio data, not line endings.
   Splitting corrupts the file. Fixed by switching to Response(content=bytes) which
   sends the full buffer in one shot with no processing."

The pattern across all four bugs: the error was silent at startup and only appeared
at runtime under a specific condition. This is why you test each phase immediately
rather than building everything first and testing at the end.

---

*This document reflects the actual working project at `E:\Fastapi_voicebot`.*
*Every code block is the exact final working version. Build it phase by phase and test at each step.*
*Last updated after all bugs were fixed and the full pipeline (text chat, PDF RAG, voice in/out) was verified end-to-end.*
