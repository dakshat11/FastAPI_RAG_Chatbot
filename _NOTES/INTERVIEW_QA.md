# Interview Q&A — RAG Voice Agent (FastAPI + LangGraph + Whisper)
### Based on the exact working project at `E:\Fastapi_voicebot`

> Every answer here references the actual code in this project.
> When asked a question, always ground your answer in something specific —
> a file name, a line of code, a decision that was made. That is what separates
> a candidate who built something from one who just read about it.

---

## Table of Contents

1. [Project Overview Questions](#1-project-overview)
2. [FastAPI Architecture](#2-fastapi-architecture)
3. [Pydantic and Schemas](#3-pydantic-and-schemas)
4. [Dependency Injection](#4-dependency-injection)
5. [LangGraph and the Agent](#5-langgraph-and-the-agent)
6. [RAG — Retrieval Augmented Generation](#6-rag)
7. [Tools](#7-tools)
8. [Voice Interface](#8-voice-interface)
9. [Database and Persistence](#9-database-and-persistence)
10. [Configuration and Environment](#10-configuration-and-environment)
11. [Bugs You Found and Fixed](#11-bugs-found-and-fixed)
12. [Python Concepts Used in This Project](#12-python-concepts)
13. [Design Decisions and Trade-offs](#13-design-decisions-and-trade-offs)
14. [Scenario / What-Would-You-Do Questions](#14-scenario-questions)
15. [Production and Scaling Questions](#15-production-and-scaling)

---

## 1. Project Overview

---

**Q: Describe this project in two sentences.**

A: It's a production-structured FastAPI backend for an AI agent that can chat, answer
questions about uploaded PDF documents, search the web, calculate, fetch stock prices,
and respond over voice. It's built in a 5-layer architecture where each layer has a
single responsibility, so features like voice can be added without touching the
existing chat or RAG logic.

---

**Q: Walk me through what happens when a user sends a text message.**

A: The HTTP request hits `POST /api/v1/chat/`. FastAPI reads the JSON body, validates
it against `ChatRequest` — if `thread_id` or `message` are missing, a `422` is
returned automatically. If valid, the `chat()` endpoint calls
`agent_service.invoke(message, thread_id)`. LangGraph loads the conversation history
for that `thread_id` from SQLite, appends the new `HumanMessage`, runs `chat_node`
which calls the LLM, and if the LLM decides to use a tool, the graph routes to
`ToolNode`, executes the tool, loops back to `chat_node`, and eventually the LLM
produces a final answer with no tool calls. LangGraph saves the updated state to
SQLite, and `invoke()` returns `result["messages"][-1].content`. The endpoint wraps
that in `ChatResponse` and returns JSON.

---

**Q: Walk me through what happens when a user sends a voice message.**

A: The audio file hits `POST /api/v1/voice/chat?thread_id=xyz`. FastAPI reads the
multipart body, the endpoint calls `voice_service.transcribe(audio_bytes)`, which
wraps the bytes in a `BytesIO` object (with `.name = "audio.mp3"` so Whisper knows
the format) and sends it to OpenAI's Whisper API. The transcribed text string is then
passed to `agent_service.invoke()` — the exact same call as the text endpoint. The
agent processes it, returns a text reply, which goes to `voice_service.synthesise()`,
which calls OpenAI's TTS API and returns raw MP3 bytes. Those bytes are returned as
a `Response(content=bytes, media_type="audio/mpeg")` with
`Content-Disposition: attachment` so it downloads as `reply.mp3`.

---

**Q: How many endpoints does this project have and what does each do?**

A:
- `GET /health` — liveness probe, returns `{"status": "healthy"}`
- `POST /api/v1/chat/` — text chat, JSON in / JSON out
- `GET /api/v1/threads/` — lists all thread IDs stored in SQLite
- `GET /api/v1/threads/{thread_id}` — metadata for one thread (has PDF, filename, chunks)
- `POST /api/v1/pdf/upload?thread_id=x` — ingests a PDF into FAISS for a thread
- `POST /api/v1/voice/chat?thread_id=x` — voice chat, audio in / audio out
- `POST /api/v1/voice/transcribe-only` — Whisper transcription only, for testing

---

**Q: Why did you use FastAPI instead of Flask or Django?**

A: Three reasons specific to this project. First, FastAPI is async-native — it uses
`async def` and ASGI, which matters when you're awaiting OpenAI API calls that could
take seconds each. Flask would block the thread during that wait. Second, FastAPI
auto-generates the Swagger UI at `/docs` from the Pydantic schemas, which is
essential for testing the voice endpoint without writing a frontend. Third, Pydantic
validation is built-in — the `422` response on bad input requires zero custom code.

---

**Q: What is the purpose of the `thread_id`?**

A: It's the key that isolates conversations. LangGraph uses it to load and save the
correct checkpoint from SQLite — different `thread_id` values are completely separate
conversations with no shared memory. It's also the key for the FAISS retriever store —
`_THREAD_RETRIEVERS[thread_id]` means each conversation can have its own uploaded PDF.
The voice endpoint shares the same `thread_id` as the text endpoint, so a user can
start a conversation by typing and continue it by speaking.

---

## 2. FastAPI Architecture

---

**Q: What is the 5-layer architecture and why does it matter?**

A: The five layers are: endpoints (`api/v1/endpoints/`), schemas (`schemas/`),
services (`services/`), core (`core/`), and models (`models/`). Each layer has one
job. Endpoints handle HTTP. Schemas define and validate data shapes. Services contain
business logic. Core holds configuration and shared infrastructure. Models define
database tables. The cardinal rule is that imports only flow downward — endpoints
import services and schemas, services import core, core imports nothing in the
codebase. If a service imported from an endpoint, you'd have a circular dependency and
would have rebuilt the monolith with more files.

---

**Q: What does `main.py` do?**

A: It creates the FastAPI `app` object, registers the `api_router` (which includes all
endpoint routers), defines the `lifespan` context manager for startup/shutdown
logging, and declares the `/health` endpoint. That is literally all. The file is
intentionally minimal — no business logic lives there. The services initialize
themselves as module-level singletons when Python first imports them, so there is
nothing to explicitly start up.

---

**Q: What is `api/v1/api.py` for and why does it exist as a separate file?**

A: It's the router aggregator. It creates one top-level `APIRouter` with prefix
`/api/v1` and calls `include_router()` for each feature's router. This file is the
only place that knows about every route. Adding a new feature — say, a `/user`
endpoint — means one import and one `include_router()` line here, and nothing else
changes. Without it, `main.py` would need to know about every single endpoint file
directly, which doesn't scale.

---

**Q: Why is the API versioned (`/api/v1/`)?**

A: When you break an API — change a field name, remove an endpoint, change the response
shape — clients that depend on the old version break. Versioning lets you deploy
`/api/v2/` with the breaking changes while keeping `/api/v1/` alive for existing
clients. Both run from the same server. In this project the prefix is set in
`api/v1/api.py` as `APIRouter(prefix="/api/v1")`, so every route under it inherits it
automatically.

---

**Q: What is the `lifespan` context manager and what replaced `@app.on_event("startup")`?**

A: `lifespan` is an `asynccontextmanager` function passed to `FastAPI(lifespan=...)`.
Code before `yield` runs on startup (before the server accepts its first request).
Code after `yield` runs on shutdown. It replaces the deprecated
`@app.on_event("startup")` and `@app.on_event("shutdown")` decorators. In this project
the lifespan just logs — the services initialize at import time — but it's the correct
place for tasks like checking that the OpenAI API is reachable, running database
migrations, or pre-loading heavy models.

---

**Q: What is ASGI and how is it different from WSGI?**

A: WSGI (used by Flask/Django) is synchronous — one request occupies one thread until
it completes. ASGI (used by FastAPI via Starlette and Uvicorn) is asynchronous — one
thread can handle thousands of concurrent requests using Python's `async/await`. When
an ASGI handler awaits an I/O operation (like an OpenAI API call), it yields control
back to the event loop, which processes other requests. In this project, every
endpoint handler is `async def`, which means while one request waits for Whisper to
return, Uvicorn can be processing other requests.

---

**Q: What is Uvicorn and what does it do?**

A: Uvicorn is the ASGI server — it's the process that listens on a TCP port, accepts
HTTP connections, and feeds them to Starlette/FastAPI. Think of it as the bridge
between the OS network stack and your Python application. You run the app with
`uvicorn main:app` or `fastapi dev main.py`. The `--reload` flag makes Uvicorn watch
the file system and restart on changes during development.

---

**Q: What does `response_model=` do in a route decorator?**

A: It tells FastAPI which Pydantic model to use for the outgoing response. FastAPI will
validate the return value against that model — any extra fields are stripped, missing
required fields cause a `500`, and the model's field definitions appear in the Swagger
docs. In `chat.py`:
```python
@router.post("/", response_model=ChatResponse)
```
This ensures the endpoint always returns `{thread_id, reply}` and nothing else, even
if the service accidentally returns extra data.

---

**Q: Why does the voice endpoint not use `response_model=`?**

A: `response_model` is for JSON responses only. The voice endpoint returns a
`Response(content=bytes, media_type="audio/mpeg")` — raw binary MP3 data. There is no
Pydantic model that can describe "a binary MP3 file". When you return a `Response`
subclass directly, FastAPI bypasses its JSON serialisation entirely and sends the bytes
straight through.

---

**Q: How does FastAPI generate the Swagger UI at `/docs`?**

A: FastAPI builds an OpenAPI spec at startup by inspecting all registered routes and
their Pydantic schemas. For each route it reads the path, HTTP method, path/query
parameters, request body schema (from the `body` parameter's type annotation), and
response schema (from `response_model=`). All `Field(description=...)` strings appear
as field descriptions in the UI. The Swagger UI at `/docs` reads this spec and renders
the interactive form. This is why writing good `Field` descriptions and docstrings
matters — they become the API documentation.

---

## 3. Pydantic and Schemas

---

**Q: What is Pydantic and what does it do in this project?**

A: Pydantic is a data validation library. When FastAPI sees a function parameter typed
as a Pydantic model (like `body: ChatRequest`), it automatically: reads the raw JSON
from the request body, attempts to parse and validate it against `ChatRequest`'s field
definitions, returns a `422 Unprocessable Entity` with a detailed error message if
anything is wrong, and gives the handler a fully typed Python object if everything is
valid. No validation code is written by hand anywhere in this project.

---

**Q: What does `Field(...)` mean in Pydantic?**

A: `Field(...)` is a Pydantic field declaration. The `...` (Ellipsis) means the field
is required — there is no default. `Field("default")` means it's optional with that
default. You can add validators: `Field(..., min_length=1)` means required and at
least 1 character long. `Field(..., description="...")` adds documentation that
appears in Swagger. In `ChatRequest`, `message: str = Field(..., min_length=1)` means
you cannot send an empty string — a `422` is returned if you do.

---

**Q: Why is there a separate schema file per resource?**

A: One schema file per resource keeps the import paths unambiguous and the files small.
`pdf.py` endpoint imports `from schemas.pdf import PDFUploadResponse`. If all schemas
lived in one file, you'd have one giant file and still need the import path to point to
a specific symbol. More importantly, when you write `from schemas.pdf import X`, the
file `schemas/pdf.py` must exist on disk — a common mistake is putting the schema
definition in a comment inside another file without creating the actual module.

---

**Q: What is the difference between a request schema and a response schema?**

A: A request schema validates data coming IN from the client. FastAPI parses the raw
JSON body into it — if fields are missing or wrong type, the request is rejected before
your handler runs. A response schema validates data going OUT to the client. FastAPI
serialises the handler's return value through it — extra fields are stripped, ensuring
the client always gets a predictable shape. In `chat.py`: `ChatRequest` is the request
schema, `ChatResponse` is the response schema.

---

**Q: What HTTP status code does Pydantic validation failure return and why?**

A: `422 Unprocessable Entity`. It means "the request was syntactically correct HTTP
but the body content failed semantic validation." It's distinct from `400 Bad Request`
(malformed HTTP) and `500 Internal Server Error` (your code crashed). FastAPI returns
a detailed JSON error body with `loc` (location of the failed field), `msg` (human
description), and `type` (Pydantic error type).

---

**Q: What is `Optional[str]` and why is it used in `ThreadInfo`?**

A: `Optional[str]` is equivalent to `Union[str, None]` — the field can be either a
string or `None`. In `ThreadInfo`, `document_filename: Optional[str] = None` means a
thread might not have a PDF uploaded. If you declared it as `document_filename: str`
and returned `None`, Pydantic would raise a validation error. The `= None` also sets
the default so you don't have to provide it when constructing `ThreadInfo`.

---

## 4. Dependency Injection

---

**Q: What is dependency injection?**

A: Dependency injection means a function receives the objects it needs from outside,
rather than creating them internally. In FastAPI, `Depends()` is the DI mechanism:
```python
@router.post("/chat")
async def chat(body: ChatRequest, service = Depends(get_agent_service)):
    return service.invoke(body.message)
```
This means the endpoint never creates the service — it's provided. You can swap
`get_agent_service` in tests to return a mock without changing the endpoint code.

---

**Q: This project uses module-level singletons instead of `Depends`. Explain the difference and when you'd use each.**

A: Module-level singletons mean `agent_service = AgentService()` sits at the bottom of
`agent_service.py`. Every import of that module gets the same object. It's DI in
spirit — the endpoint imports and uses the service rather than creating it — but
without the FastAPI `Depends` machinery. The benefit is simplicity. The cost is that
you cannot easily swap the service per-request.

`Depends()` is superior when the injected object has a lifecycle tied to the request:
a database session that must be committed or rolled back, a user object extracted from
an auth token, or a feature flag that changes per-request. For this project's services
(which are stateless across requests, using thread_id for state isolation), singletons
are the right call.

---

**Q: The `get_checkpointer()` function in `database.py` exists but isn't used. Why is it there?**

A: It's a forward-looking DI factory. Currently the checkpointer is imported directly
(`from core.database import checkpointer`). If you later switch to PostgreSQL with an
async connection pool, you'd change `get_checkpointer()` to open and close a
connection per-request, then inject it via `Depends(get_checkpointer)`. Having the
factory in place means the migration path is clear — only `database.py` and the
`Depends(...)` callsite change.

---

## 5. LangGraph and the Agent

---

**Q: What is LangGraph and why did you use it instead of a simple LangChain chain?**

A: LangGraph is a library for building stateful, cyclical agent workflows. A LangChain
chain is linear — A → B → C → done. LangGraph allows loops: the LLM can call a tool,
see the result, call another tool, see that result, and only then answer. That loop is
what makes this an "agent." Additionally, LangGraph has a built-in checkpointer
interface that saves the full conversation state to SQLite after every node execution,
which is how conversation memory works across HTTP requests.

---

**Q: What is `ChatState` and why does `messages` use `Annotated`?**

A: `ChatState` is a `TypedDict` that represents the entire memory of the graph for one
run. The `messages` field holds the conversation history. The `Annotated[list[BaseMessage], add_messages]`
syntax attaches a **reducer** to the field. When a graph node returns
`{"messages": [new_message]}`, LangGraph doesn't replace the list — it calls the
`add_messages` reducer which appends the new message to the existing list. Without this
annotation, each node invocation would wipe the history.

---

**Q: What is the difference between a chatbot and an agent?**

A: A chatbot calls the LLM once and returns the answer. An agent uses a loop: the LLM
can decide to call a tool, receive the tool's result, then decide to call another tool
or answer directly. In this project, the graph loops between `chat_node` (LLM reasoning)
and `tools` (tool execution) until the LLM produces a response with no tool calls.
`tools_condition` is the branching logic — it reads the last message and routes to
`tools` if there are tool calls, or to `END` if there aren't.

---

**Q: Explain how `tools_condition` works.**

A: `tools_condition` is a pre-built LangGraph function used in
`graph.add_conditional_edges("chat_node", tools_condition)`. After `chat_node` runs
and returns an `AIMessage`, `tools_condition` inspects that message. If
`message.tool_calls` is non-empty, it returns the string `"tools"`, routing to the
`tools` node. If `tool_calls` is empty, it returns `"__end__"`, routing to `END`. This
creates the agent loop automatically without any custom routing logic.

---

**Q: What does `graph.compile(checkpointer=checkpointer)` do?**

A: `compile()` turns the `StateGraph` definition (nodes and edges) into an executable
`CompiledGraph` object that can be called with `.invoke()`. Passing the checkpointer
tells LangGraph to save the full graph state to the database after every node execution.
Before each invocation, it also loads the most recent saved state for the given
`thread_id`. Without the checkpointer, the graph has no memory between HTTP requests.

---

**Q: What is the `config` dict and why does it have `"configurable"` as a key?**

A: The `config` dict is passed to every LangGraph invocation:
```python
config = {"configurable": {"thread_id": thread_id}}
self._graph.invoke(state, config=config)
```
The `"configurable"` key is LangGraph's convention for runtime configuration values.
The `SqliteSaver` checkpointer reads `config["configurable"]["thread_id"]` to know
which row in the SQLite database to load and save. The `chat_node` also reads this
config to know which thread is active (for the RAG tool hint). It flows through every
node automatically.

---

**Q: Why is `rag_tool` defined inside `_build_graph()` rather than in `tools.py`?**

A: Two reasons. First, `rag_tool` needs to accept a `thread_id` argument at call time
to look up the right FAISS retriever from `_THREAD_RETRIEVERS`. This is fundamentally
different from `calculator` or `search_tool` which are fully stateless. Second, and
more critically, `ToolNode` must know about every tool at compile time. If `rag_tool`
were defined in `tools.py` and only added to `bind_tools` dynamically, `ToolNode`
would not have it and would crash with "Tool not found" when the LLM called it.
Defining it inside `_build_graph()` ensures it's registered in both `llm.bind_tools()`
and `ToolNode(all_tools)` simultaneously.

---

**Q: What does `bind_tools` do?**

A: `llm.bind_tools(all_tools)` sends the JSON schema of each tool to the OpenAI API
alongside every message. OpenAI's function-calling feature reads these schemas and can
return structured tool call objects in the response instead of plain text. The schema
is built from two things: the function's type annotations (which become the parameter
schema) and the docstring (which becomes the tool description the LLM reads to decide
when to use it). A vague docstring means the LLM won't know when to call the tool.

---

**Q: What is a `ToolNode` and why must its tool list match `bind_tools`?**

A: `ToolNode` is a pre-built LangGraph node that receives an `AIMessage` with
`tool_calls`, finds the matching Python function by name, calls it with the provided
arguments, and returns the result as a `ToolMessage`. It maintains an internal dict of
`{tool_name: tool_function}`. If the LLM calls a tool that is in `bind_tools` but not
in `ToolNode`, the lookup fails and raises `ValueError: Tool <name> not found`. The
two lists must be identical — same objects, same names.

---

**Q: Explain the LangGraph graph structure of this project.**

A:
```
START → chat_node
            ↓
      tools_condition
       ↙            ↘
   "tools"          "__end__"
      ↓                 ↓
  tool_node            END
      ↓
  chat_node  (edge back — creates the loop)
```
`graph.add_edge(START, "chat_node")` — always start here.
`graph.add_conditional_edges("chat_node", tools_condition)` — branch based on tool calls.
`graph.add_edge("tools", "chat_node")` — always loop back after tool execution.

The loop terminates when `chat_node` produces an `AIMessage` with no `tool_calls`.

---

**Q: What is `add_messages` and how does it prevent overwriting history?**

A: `add_messages` is a reducer function from `langgraph.graph.message`. When a node
returns `{"messages": [new_msg]}`, LangGraph calls `add_messages(existing_list, [new_msg])`
which appends the new message to the existing history. Without it, the `messages` field
would be replaced entirely by `[new_msg]` on each node execution, wiping all prior
context. The `Annotated[list[BaseMessage], add_messages]` syntax is how you attach a
reducer to a TypedDict field in LangGraph.

---

## 6. RAG

---

**Q: What is RAG and why is it needed?**

A: RAG stands for Retrieval-Augmented Generation. LLMs are trained on data up to a
cutoff date and have no knowledge of your specific documents. Rather than fine-tuning
the model (expensive, slow, requires ML expertise), RAG retrieves relevant text from
your documents at query time and injects it into the LLM's context window. The LLM
then answers using both its training knowledge and the provided context. In this
project, a PDF is uploaded, chunked, embedded into vectors, and stored in FAISS. When
the user asks about the PDF, the most similar chunks are retrieved and sent to the LLM.

---

**Q: Walk through the full PDF ingestion pipeline.**

A:
1. The PDF bytes arrive at `POST /api/v1/pdf/upload?thread_id=x`
2. The endpoint calls `rag_service.ingest_pdf(file_bytes, thread_id, filename)`
3. `PyPDFLoader` requires a real file path, so bytes are written to a temp file
4. `PyPDFLoader` reads the temp file and returns a list of `Document` objects (one per page)
5. `RecursiveCharacterTextSplitter` splits each document into chunks of ~1000 characters
   with 200 characters of overlap between consecutive chunks
6. `OpenAIEmbeddings` converts each chunk's text into a vector (1536 floats for `text-embedding-3-small`)
7. `FAISS.from_documents()` builds an in-memory vector index from all chunk vectors
8. `.as_retriever(search_type="similarity", search_kwargs={"k": 4})` wraps the index
9. The retriever is stored in `_THREAD_RETRIEVERS[thread_id]`
10. The temp file is deleted (FAISS has its own copy in RAM)

---

**Q: What is an embedding and why does similarity search work?**

A: An embedding is a list of numbers (a vector) that represents the semantic meaning
of a piece of text. The embedding model (`text-embedding-3-small`) maps semantically
similar text to vectors that are numerically close together in a high-dimensional space.
"What are the penalties?" and "What are the fines for violations?" produce vectors that
are close to each other even though they share no words. When a user asks a question,
it's embedded using the same model, and FAISS finds the chunks whose vectors are
closest to the query vector — those chunks are the most semantically relevant.

---

**Q: What is FAISS and why was it chosen?**

A: FAISS (Facebook AI Similarity Search) is a library for fast nearest-neighbor search
in high-dimensional vector spaces. It keeps its index entirely in RAM, which makes
similarity searches extremely fast. It was chosen because it requires no external
service — no database setup, no network calls. The trade-off is that it's not
persistent: a server restart wipes all uploaded PDFs. For a demo or prototype, FAISS
is perfect. For production, you'd swap it for ChromaDB (disk-persistent) or Pinecone
(cloud-hosted). The interface in this project (`retriever.invoke(query)`) would not
change.

---

**Q: Why does the text splitter use chunk overlap?**

A: If a key sentence spans the boundary between two chunks — the first half at the end
of chunk N, the second half at the start of chunk N+1 — without overlap neither chunk
contains the full sentence. With `chunk_overlap=200`, chunk N+1 starts 200 characters
back into chunk N's content. The sentence appears fully in chunk N+1. This significantly
improves retrieval quality for information that happens to be split at a chunk boundary.
The cost is slightly more total chunks and slightly more storage.

---

**Q: Why is the embeddings client (`_embeddings`) a module-level variable rather than created inside `ingest_pdf`?**

A: Creating an `OpenAIEmbeddings` object initialises an HTTP client. If you created it
inside `ingest_pdf()`, you'd initialise a new HTTP client on every PDF upload. Module-level
means it's created once when `rag_service.py` is first imported and reused for every
upload. The object is stateless (it just makes API calls) so sharing it across uploads
is safe.

---

**Q: Why does PyPDFLoader need a real file path when we have the bytes already in memory?**

A: `PyPDFLoader` internally opens a file using standard file I/O operations — it wasn't
designed to accept raw bytes. It needs an OS path. The solution is `tempfile.NamedTemporaryFile`
which creates an actual file on disk, we write the bytes to it, give the path to the loader,
and delete the temp file afterwards. The `finally:` block ensures the temp file is always
deleted even if an exception occurs during ingestion.

---

**Q: Where does FAISS data go when the server restarts?**

A: It disappears. `_THREAD_RETRIEVERS` is a plain Python dict in memory. When the
Python process ends, it's gone. The uploaded PDFs and their vector indices are not
persisted anywhere. The conversation history in SQLite (`chatbot.db`) survives restarts,
but the RAG knowledge does not. To fix this in production, swap FAISS for ChromaDB
which writes its index to disk, or Pinecone which stores it in the cloud.

---

**Q: How does `rag_tool` know which retriever to use?**

A: It takes `thread_id` as an argument. The LLM is instructed to always pass the
current `thread_id` when calling it:
```python
@tool
def rag_tool(query: str, thread_id: str = "") -> dict:
    retriever = rag_service.get_retriever(thread_id)
```
`get_retriever(thread_id)` does `_THREAD_RETRIEVERS.get(thread_id)` — a simple dict
lookup. If no PDF has been uploaded for that thread, it returns `None` and the tool
returns an error message (not an exception) so the LLM can relay it to the user.

---

**Q: What is `retriever_k` and what happens if you set it too high or too low?**

A: `retriever_k` (default: 4) is the number of chunks returned by each FAISS search.
Too low (k=1): you might miss relevant context if the answer spans multiple chunks.
Too high (k=20): you inject a lot of text into the LLM's context window, increasing
cost (more tokens) and potentially diluting the relevant information with unrelated
chunks. 4 chunks × ~1000 characters = ~4000 characters of context, which is a
reasonable balance for most documents.

---

## 7. Tools

---

**Q: What does the `@tool` decorator do?**

A: It converts a plain Python function into a LangChain `Tool` object that the LLM
can call. It does two things automatically: reads the function's type annotations
(`first_num: float`, `operation: str`) to build a JSON schema that OpenAI uses for
function calling, and reads the docstring to create the tool's description — the text
the LLM reads to decide when and why to use this tool. Both are required. Missing
annotations = LLM doesn't know what to pass. Missing or vague docstring = LLM doesn't
know when to call it.

---

**Q: What makes a tool "stateless" and why does it matter?**

A: A stateless tool produces the same output given the same inputs, with no dependency
on which user, session, or thread is calling it. `calculator(5, 3, "add")` always
returns `8` regardless of context. This means the tool object can be safely shared
across all requests and all threads. `rag_tool` is the exception — it depends on
`thread_id` to look up the right FAISS retriever. That is why it lives in
`agent_service.py` (built at graph compile time with knowledge of `rag_service`) rather
than in `tools.py`.

---

**Q: Why does `calculator` return a dict with an `"error"` key instead of raising an exception?**

A: When a tool raises an exception, LangGraph catches it and converts it to an error
`ToolMessage`. The LLM sees something like "Tool execution failed: division by zero"
and may not handle it gracefully. When a tool returns `{"error": "Division by zero"}`,
the LLM receives a structured dict, reads the error message, and can relay it to the
user naturally: "I can't divide by zero, please provide a non-zero divisor." Returning
errors as data is the more user-friendly pattern for tools.

---

**Q: How does the LLM decide which tool to call?**

A: OpenAI's function-calling feature works like this: when you call
`llm.bind_tools(all_tools)`, the tool schemas are sent with every API request. The
model reads the schemas and docstrings and, based on the conversation, decides whether
to call a tool and which one. It returns either plain text (a direct answer) or a
structured `tool_calls` object with the tool name and arguments. The model doesn't
"see" the Python code — it only sees the schema (parameter names and types) and the
docstring.

---

**Q: Why does `get_stock_price` use `r.raise_for_status()`?**

A: `requests.get()` doesn't raise an exception on HTTP error responses like `404` or
`500` — it just returns a response object with a bad status code. `r.raise_for_status()`
explicitly raises a `requests.exceptions.HTTPError` if the status code indicates an
error. This ensures the `except Exception as e` block catches API errors and returns
them as `{"error": str(e)}` to the LLM, rather than silently returning a response body
that might be an error JSON from Alpha Vantage.

---

## 8. Voice Interface

---

**Q: Describe the voice pipeline end to end.**

A:
1. Client sends a `POST /api/v1/voice/chat?thread_id=x` with an audio file
2. FastAPI reads the multipart body, the endpoint reads the bytes
3. `voice_service.transcribe(audio_bytes, filename)` wraps bytes in `io.BytesIO`,
   sets `.name = filename` (so Whisper knows the audio format), sends to OpenAI
   Whisper API, returns a plain text string
4. If transcript is empty, return `422`
5. `agent_service.invoke(transcript, thread_id)` — identical call to the text endpoint,
   the agent doesn't know the input came from audio
6. `voice_service.synthesise(reply_text)` sends the text to OpenAI TTS, returns raw MP3 bytes
7. `Response(content=bytes, media_type="audio/mpeg", headers={...})` sends the file

---

**Q: Why is `Response` used instead of `StreamingResponse` for the audio?**

A: `StreamingResponse` iterates over a file-like object (`BytesIO`) by splitting on
`\n` bytes (byte value `0x0A`). MP3 is raw binary audio data — `0x0A` appears
throughout as part of the audio encoding, not as a line ending. Iterating splits the
MP3 stream at those bytes, corrupting the file. The client downloads a file that no
audio player can decode. `Response(content=bytes)` sends the entire buffer in one
write operation with zero processing, which is correct for any binary format.
Additionally, since OpenAI's TTS returns all bytes synchronously (not as a stream),
there is no benefit to streaming.

---

**Q: Why does `BytesIO` need a `.name` attribute when sending to Whisper?**

A: `io.BytesIO` is an in-memory file object. It has no filename. OpenAI's Whisper API
uses the filename's extension (`.mp3`, `.wav`, `.m4a`) to know which audio decoder to
use. The OpenAI Python SDK reads `file.name` when preparing the multipart request. By
setting `audio_file.name = filename` (e.g., `"audio.mp3"`), we give Whisper the
format hint it needs without writing anything to disk. Without this, Whisper might
reject the file or mis-decode it.

---

**Q: Why is `Content-Disposition: attachment` used instead of `inline`?**

A: `Content-Disposition: attachment; filename=reply.mp3` tells every HTTP client
(browser, Swagger UI, curl) to treat the response as a file download. It shows a
"Download file" link in Swagger UI and a save dialog in browsers. `inline` tells the
browser to try to render/play the content in-page. Swagger UI has no audio player, so
`inline` results in nothing happening — no download button, no playback. `attachment`
is the correct choice for any binary response in an API context.

---

**Q: What is `_safe_header()` and why is it needed?**

A: HTTP/1.1 uses `\r\n` as the delimiter between header lines in the protocol. A
header value that contains a literal `\n` byte breaks the HTTP protocol — the parser
treats it as the start of a new header line (HTTP Header Injection vulnerability).
Uvicorn correctly rejects such values with `RuntimeError: Invalid HTTP header value`.

LLM replies almost always contain newlines — bullet points, numbered lists, paragraphs.
Putting `reply_text` directly into `X-Reply-Text` crashes the server on any structured
answer. `_safe_header()` replaces `\r\n`, `\n`, and `\r` with spaces before setting
the header value. The order matters: `\r\n` must be replaced first (it's two characters)
— if you replace `\n` first, lone `\r` characters remain, which are also illegal.

---

**Q: The voice and text endpoints share the same `thread_id`. What does this mean in practice?**

A: A user can start a conversation by typing, switch to speaking mid-conversation, and
continue seamlessly. Both endpoints call `agent_service.invoke(message, thread_id)`
which loads the same LangGraph checkpoint from SQLite. The agent's history is the same
regardless of which modality sent each message. The agent doesn't store modality
information — it only stores `HumanMessage` and `AIMessage` objects.

---

**Q: Why does `voice_service.py` use the OpenAI SDK directly instead of LangChain?**

A: LangChain has no wrappers for OpenAI's audio APIs (Whisper and TTS). LangChain
wraps the chat completions and embeddings APIs. For audio, you use the OpenAI Python
SDK directly: `client.audio.transcriptions.create()` and
`client.audio.speech.create()`. The OpenAI client is created once in `VoiceService.__init__`
and reused for every request (same API key as the LLM, different endpoint paths).

---

**Q: What Whisper input formats are supported?**

A: mp3, mp4, mpeg, mpga, m4a, wav, and webm. The format is communicated via the
`file.name` attribute on the `BytesIO` object. In the endpoint, `file.filename or "audio.mp3"`
is used as a fallback — if the client doesn't send a filename (e.g., via some HTTP clients),
it defaults to `audio.mp3`. The content type header is not validated strictly in the
voice endpoint (unlike the PDF endpoint which checks for `application/pdf`) because
audio content types vary widely between clients.

---

## 9. Database and Persistence

---

**Q: What database does this project use and what does it store?**

A: SQLite, accessed via the `SqliteSaver` checkpointer from `langgraph-checkpoint-sqlite`.
It stores the full LangGraph state for every thread after every node execution —
meaning the complete message history (all `HumanMessage`, `AIMessage`, and `ToolMessage`
objects) is serialised and saved. The database file is `chatbot.db` in the project root.
It does NOT store the FAISS vector indices — those live only in RAM.

---

**Q: Why is `check_same_thread=False` passed to `sqlite3.connect()`?**

A: SQLite's Python binding by default only allows the thread that created the connection
to use it. FastAPI's Uvicorn server uses a thread pool — different requests may be
handled by different threads. Without `check_same_thread=False`, the second request on
a different thread would get `ProgrammingError: SQLite objects created in a thread can
only be used in that same thread`. The flag disables this restriction, allowing the
single shared connection to be used from any thread.

---

**Q: What files are created by SQLite and why are there three (`.db`, `.db-shm`, `.db-wal`)?**

A: SQLite uses Write-Ahead Logging (WAL) mode for concurrent write safety.
- `.db` — the main database file
- `.db-shm` — shared memory file, used for inter-process coordination of WAL readers
- `.db-wal` — the write-ahead log, where uncommitted writes are staged before being
  checkpointed into the main file

These three files together form one logical database. All three are in `.gitignore`
because they're runtime state, not source code.

---

**Q: What would you use instead of SQLite in production?**

A: PostgreSQL with async SQLAlchemy. SQLite is a single-file database with no network
access, limited concurrent write support, and no replication. For a production API
serving multiple instances (e.g., behind a load balancer), you need a database that
all instances can connect to simultaneously. LangGraph has a `PostgresSaver` checkpointer
for exactly this. The `get_checkpointer()` function in `database.py` exists as the
injection point — only that function and its dependencies would change.

---

## 10. Configuration and Environment

---

**Q: How does `core/config.py` work?**

A: `Settings` inherits from `pydantic_settings.BaseSettings`. When Python imports this
module, `settings = Settings()` is executed, which triggers `BaseSettings` to read the
`.env` file (specified in `class Config`) and map each variable to a typed Python field.
`openai_api_key: str` has no default, so it's required — if it's missing from `.env`,
a `ValidationError` is raised immediately at startup. All other fields have defaults
and can optionally be overridden in `.env`.

---

**Q: Why must `.env` values have no quotes and no spaces around `=`?**

A: `pydantic-settings` reads the `.env` file literally. The value is everything between
the `=` sign and the end of the line. `KEY="value"` means the value is `"value"` —
with the double-quote characters included. When that string is passed to the OpenAI SDK
as an API key, the key starts with `"`, which OpenAI rejects with a `401`. Similarly,
`KEY = value` means the value starts with a space. The correct format is `KEY=value`
with no surrounding characters.

---

**Q: Why is `settings` a module-level singleton rather than instantiated per request?**

A: `Settings()` reads the `.env` file from disk. Reading a file on every HTTP request
is wasteful and unnecessary — the configuration doesn't change between requests.
Module-level means the file is read exactly once when Python first imports `core/config.py`.
Every subsequent import of `settings` gets the same cached object. This is one of the
most common singleton patterns in Python.

---

**Q: How would you change the LLM model without touching application code?**

A: Add `MODEL_NAME=gpt-4o` to your `.env` file. The `Settings` class has
`model_name: str = "gpt-4o-mini"` with a default. `pydantic-settings` reads
environment variables (and `.env` files) and overrides field values that match. The
`AgentService` reads `settings.model_name` at init time, so the new model is used
automatically on the next server start.

---

**Q: Why is `chatbot.db` in `.gitignore`?**

A: It's a runtime artefact, not source code. The database file is created fresh when
the app starts for the first time in a new environment. Committing it would mean
everyone who clones the repo starts with your conversation history, test data, and any
sensitive information from previous conversations. Runtime data (databases, log files,
compiled bytecode) should never be committed.

---

## 11. Bugs Found and Fixed

---

**Q: You got a 422 error on PDF upload. What caused it and how did you fix it?**

A: The original endpoint used `Form(...)` for `thread_id` alongside `File(...)` for
the PDF. When a route uses `File()`, the entire request body must be
`multipart/form-data`. `Form()` fields in that context must also be sent as multipart
text fields — not as query parameters, not as JSON. Most HTTP clients (Postman,
browser fetch, curl without the right flags) don't do this automatically, sending
`thread_id` incorrectly and triggering a `422 Field required` validation error.

The fix was changing `thread_id: str = Form(...)` to `thread_id: str = Query(...)`.
This moves `thread_id` to the URL as `?thread_id=abc`. The file stays in the multipart
body. Every HTTP client handles query parameters correctly, eliminating the confusion.

---

**Q: You got a "Tool not found" crash. What caused it?**

A: The original code built `ToolNode` with only the base tools (calculator, search,
stock price) but then dynamically added `rag_tool` to the LLM's `bind_tools` call
inside `chat_node`. So the LLM knew it could call `rag_tool`, but when it did,
`ToolNode` looked through its registered tools, didn't find `rag_tool`, and raised
`ValueError: Tool rag_tool not found`.

The fix was defining `rag_tool` inside `_build_graph()` and adding it to `all_tools`,
which is passed to both `bind_tools` and `ToolNode`. The tool does a live lookup of
`rag_service.get_retriever(thread_id)` at call time, so it doesn't need to be created
per-thread — one definition at compile time, correct behaviour at runtime.

---

**Q: You got a `RuntimeError: Invalid HTTP header value`. What caused it?**

A: The `StreamingResponse` headers dict contained `reply_text[:500]` directly. LLM
replies almost always contain newline characters (bullet points, numbered lists). HTTP
headers cannot contain newline characters — `\n` is the protocol delimiter between
header lines. Putting a raw newline into a header value breaks the HTTP protocol (HTTP
Header Injection). Uvicorn correctly rejects this with a `RuntimeError`.

The fix was `_safe_header()`: replace `\r\n`, `\n`, `\r` with spaces (in that order
— `\r\n` first to avoid leaving a lone `\r`) before putting any text into a header.

---

**Q: The audio downloaded but wouldn't play. What caused it?**

A: `StreamingResponse` was used with `io.BytesIO(audio_bytes)`. Starlette's
`StreamingResponse` iterates over file-like objects by splitting on `\n` bytes
(`0x0A`). MP3 is raw binary audio — the byte `0x0A` appears throughout as part of
the audio encoding. Iterating over the `BytesIO` split those bytes, breaking the MP3
frame structure. The client received corrupted fragments that no audio player could
decode.

The fix was replacing `StreamingResponse` with `Response(content=audio_bytes)`. This
sends the entire byte buffer in a single write with no iteration and no byte-level
processing. Since TTS returns all bytes synchronously, there's no advantage to
streaming anyway.

---

**Q: There was a bug where API keys with quotes in `.env` caused 401 errors. Why?**

A: `pydantic-settings` reads `.env` values literally. If the file contained
`OPENAI_API_KEY= "sk-proj-..."` (with a space and quotes), the Python string became
`' "sk-proj-..."'` — leading space, double-quote, the key, double-quote. The OpenAI
API received an Authorization header with a key that started with a space and a
double-quote character. OpenAI rejected it as invalid, returning 401. The app started
normally (no startup error) and failed silently on every LLM call.

---

## 12. Python Concepts

---

**Q: What is a module-level singleton and how is it used in this project?**

A: A module-level singleton is an object created at the module's top level (outside
any class or function). In Python, a module is imported at most once per process — the
first `import` runs the module's code and caches it; subsequent imports return the
cached module. So `agent_service = AgentService()` at the bottom of
`agent_service.py` runs exactly once, no matter how many endpoints import it. Every
import gets the same `agent_service` object.

---

**Q: What is `TypedDict` and why is it used for `ChatState`?**

A: `TypedDict` creates a dictionary type with a fixed set of keys and specific value
types for each key. It's a type hint tool — `ChatState` tells type checkers (and
developers reading the code) that the state dict always has a `messages` key holding a
list of `BaseMessage` objects. LangGraph requires states to be `TypedDict` or Pydantic
models. Unlike a regular dict, `TypedDict` gives you IDE autocomplete and type
checking.

---

**Q: What is a closure and where is it used in this project?**

A: A closure is a function defined inside another function that "captures" variables
from the outer function's scope. In `agent_service.py`, `rag_tool` is defined inside
`_build_graph()`. It captures `rag_service` from the outer scope. When `rag_tool` is
called later (at request time), it still has access to `rag_service` even though
`_build_graph()` has long since returned. This is how `rag_tool` can call
`rag_service.get_retriever(thread_id)` without having `rag_service` passed as a
parameter.

---

**Q: What is `asynccontextmanager` and where is it used?**

A: `@asynccontextmanager` is a decorator from `contextlib` that turns an `async def`
generator function into an async context manager. In `main.py`, the `lifespan`
function is decorated with it and passed to `FastAPI(lifespan=lifespan)`. Code before
`yield` runs on startup, code after `yield` runs on shutdown. It's the async equivalent
of a `with` statement — FastAPI calls `__aenter__` (runs to `yield`) on startup and
`__aexit__` (runs after `yield`) on shutdown.

---

**Q: What is `io.BytesIO` and why is it used in `voice_service.py`?**

A: `io.BytesIO` is an in-memory binary stream that implements the file-like interface
(`.read()`, `.write()`, `.seek()`, `.name`). It wraps raw bytes (`bytes` type) as if
they were a file object. It's used because OpenAI's Python SDK expects a file-like
object with a `.name` attribute when sending audio for transcription — it cannot accept
raw `bytes` directly. `BytesIO` provides that interface without writing anything to
disk.

---

**Q: What is `tempfile.NamedTemporaryFile` and why is `delete=False` needed?**

A: `NamedTemporaryFile` creates a real file on disk with a guaranteed unique name.
`delete=False` means the file is NOT automatically deleted when the `with` block exits.
This is needed because `PyPDFLoader` opens the file by path after the `with` block ends.
If `delete=True` (the default), the file would be deleted when the `with` block exits,
and `PyPDFLoader` would get a "file not found" error. The `finally:` block manually
calls `os.remove(temp_path)` after loading is complete.

---

**Q: What is the `finally:` block in `ingest_pdf()` for?**

A: `finally:` runs unconditionally — whether the `try:` block succeeds, raises an
exception, or returns early. It's used here to guarantee the temp file is always
deleted, even if `PyPDFLoader` raises an exception (corrupted PDF, read error, etc.).
Without `finally:`, an exception mid-ingestion would leave temp files on disk. The
`except OSError: pass` inside `finally:` handles the case where the file was already
deleted by the OS.

---

**Q: Why is `str(thread_id)` called when storing to `_THREAD_RETRIEVERS`?**

A: Defensive programming. `thread_id` is typed as `str` in all schemas and function
signatures, but Python's type hints aren't enforced at runtime. A caller could
accidentally pass an integer. `str(thread_id)` ensures the dict key is always a string,
preventing subtle bugs where `_THREAD_RETRIEVERS[1]` and `_THREAD_RETRIEVERS["1"]`
would be different keys.

---

## 13. Design Decisions and Trade-offs

---

**Q: Why are services singletons rather than instantiated per request?**

A: Services like `AgentService` contain expensive objects — the `ChatOpenAI` client
(HTTP connection pool), the compiled LangGraph graph, the FAISS retriever store.
Creating them per request would add 100-500ms of initialisation time to every request
and waste memory. The singleton is created once at startup and reused. Thread safety
is maintained because the services themselves are stateless across requests — all
per-request state lives in LangGraph's checkpointer (SQLite) keyed by `thread_id`.

---

**Q: Why is there a `models/` directory if it's empty?**

A: It signals intent and reserves the namespace. When you add SQLAlchemy or another
ORM later, you know exactly where database table definitions go. Having the directory
and `__init__.py` in place means adding ORM models requires no restructuring. Without
it, when you add models later, you'd also have to restructure imports. An empty
directory with an `__init__.py` is a zero-cost placeholder.

---

**Q: Why does the threads endpoint import from `rag_service` even though RAG is a "later phase" feature?**

A: The endpoint returns `ThreadInfo` which includes `has_document` and
`document_filename` — metadata about whether a PDF was uploaded for a thread. This
information lives in `rag_service`. The endpoint was designed to be the complete
picture of a thread's state, combining both conversation history (from
`agent_service`) and document state (from `rag_service`). Separating them would
require two API calls from the client.

---

**Q: Should the voice endpoint validate the audio file's content type?**

A: The PDF endpoint validates `file.content_type != "application/pdf"`. The voice
endpoint deliberately does not validate content type. Audio content types vary wildly
between clients — `audio/mpeg`, `audio/mp3`, `audio/wav`, `audio/webm`,
`application/octet-stream` (generic binary). Strict validation would break legitimate
clients. Whisper is robust and handles format detection via the filename extension —
if the audio is invalid, Whisper returns an error that the `except Exception` block
catches and converts to a `500`.

---

**Q: What is the trade-off of using `gpt-4o-mini` vs `gpt-4o`?**

A: `gpt-4o-mini` is faster and cheaper — roughly 15× cheaper per token than `gpt-4o`.
For conversational tasks with structured tools, it performs well. `gpt-4o` is better
at complex reasoning, nuanced instructions, and tasks that benefit from a larger model.
In this project, `gpt-4o-mini` is the default but it's configurable via `MODEL_NAME`
in `.env`. The switch requires no code change.

---

**Q: What happens if two users upload PDFs with the same `thread_id` simultaneously?**

A: The second upload would overwrite the first in `_THREAD_RETRIEVERS`. This is a race
condition — Python's GIL prevents truly simultaneous dict writes but async code can
interleave. In practice, thread_ids should be unique per user session (e.g., a UUID),
so collision is unlikely. For multi-user production use, thread_ids should be namespaced
(e.g., `{user_id}:{session_id}`) and upload should be rate-limited per user.

---

**Q: Why does the project use `uv` instead of `pip` for package management?**

A: `uv` is a modern Python package manager written in Rust. It's significantly faster
than `pip` for both resolving dependencies and installing packages — typically 10-100×
faster. It also produces a `uv.lock` file (equivalent to `requirements.txt` with
pinned versions) for reproducible builds. The `pyproject.toml` is the source of truth
for dependencies; `uv sync` installs exactly what's specified.

---

## 14. Scenario Questions

---

**Q: A user reports that the agent isn't answering questions about their PDF. How do you debug it?**

A: Three steps. First, call `GET /api/v1/threads/{thread_id}` — if `has_document` is
`false`, the PDF was never successfully ingested (either the upload failed or the wrong
`thread_id` was used). Second, if `has_document` is `true`, test with a simple direct
question like "summarise the document" — this forces the LLM to use `rag_tool`. If
that works but specific questions don't, the chunking might not be capturing the
relevant sections. Third, check if the LLM is actually calling `rag_tool` by looking
at the raw agent messages — if it's answering from training data without calling the
tool, the system prompt hint might not be strong enough.

---

**Q: The voice endpoint works in testing but users complain it's slow. What are the bottlenecks?**

A: There are three serial API calls: Whisper transcription (300-800ms), the agent
LangGraph loop which may include tool calls (500-3000ms depending on how many tools
are called), and TTS synthesis (500-1000ms). Total latency is 1.3-5 seconds. To
reduce it: use `tts-1` over `tts-1-hd` (already the default, lower latency), route
simple factual questions to `gpt-4o-mini` (already the default), consider streaming
TTS output back as it's generated rather than waiting for the full audio (requires
switching to a streaming TTS response and `StreamingResponse` — but only for the TTS
bytes, not the full binary file). The Whisper call cannot be parallelised (it must
precede the agent call).

---

**Q: How would you add user authentication to this API?**

A: Using FastAPI's `Depends`. Create a `get_current_user` dependency that reads an
`Authorization: Bearer <token>` header, validates the JWT, and returns the user object.
Add it to each endpoint:
```python
@router.post("/chat")
async def chat(body: ChatRequest, user = Depends(get_current_user)):
    thread_id = f"{user.id}:{body.thread_id}"  # namespace by user
```
The `thread_id` should be namespaced with the user ID to prevent cross-user data access.
No changes to services are needed — the namespaced thread_id handles isolation.

---

**Q: How would you make the PDFs persist across server restarts?**

A: Replace FAISS with ChromaDB (local disk persistence) or Pinecone/Weaviate (cloud).
Only `rag_service.py` changes — the `ingest_pdf()` method would write to ChromaDB
instead of FAISS, and `get_retriever()` would read from it. The `rag_tool` in
`agent_service.py` calls `rag_service.get_retriever(thread_id)` — that interface
stays identical. No endpoints change. This is exactly why the retriever is abstracted
behind `rag_service` methods.

---

**Q: How would you add a rate limiter to the voice endpoint?**

A: Using a FastAPI middleware or the `slowapi` library. At the middleware level:
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@router.post("/chat")
@limiter.limit("10/minute")
async def voice_chat(request: Request, ...):
```
Voice is the most expensive endpoint (three API calls), so rate limiting it specifically
prevents abuse. The rate limit key can be IP address, user ID (if auth is added), or
`thread_id`.

---

**Q: How would you handle a very large PDF (500 pages, 2M characters)?**

A: Three changes. First, increase `chunk_size` and `chunk_overlap` in settings, or
keep them the same but accept more chunks. Second, the FAISS index will be larger but
still works. The real issue is time — embedding 500 pages × ~3 chunks/page = ~1500
API calls to the embeddings endpoint. Third, run ingestion as a background task rather
than blocking the HTTP response:
```python
from fastapi import BackgroundTasks
@router.post("/upload")
async def upload_pdf(background_tasks: BackgroundTasks, ...):
    background_tasks.add_task(rag_service.ingest_pdf, file_bytes, thread_id)
    return {"message": "Processing started, check back shortly"}
```
The client gets an immediate response and polls for completion.

---

**Q: A new developer joins. What's the fastest way to explain where to find things?**

A: "There are five directories. If it's about HTTP routing, look in `api/v1/endpoints/`.
If it's about data shapes and validation, look in `schemas/`. If it's about business
logic — the LLM, RAG, tools, voice transcription — look in `services/`. If it's about
configuration or database connections, look in `core/`. The dependency arrow only
points downward: endpoints depend on services, services depend on core. Nothing in
core ever imports from services or endpoints. That single rule is all you need to know
to find any bug or add any feature."

---

**Q: How would you write a test for `agent_service.invoke()`?**

A: Mock `self._llm` to return a predetermined `AIMessage` without calling the OpenAI API:
```python
from unittest.mock import MagicMock, patch
from langchain_core.messages import AIMessage

def test_invoke_returns_reply():
    with patch("services.agent_service.ChatOpenAI") as mock_llm:
        mock_llm.return_value.bind_tools.return_value.invoke.return_value = \
            AIMessage(content="Paris")
        service = AgentService()
        result = service.invoke("What is the capital of France?", "test-thread")
        assert result == "Paris"
```
The `rag_service` singleton can be patched similarly for RAG tests.

---

## 15. Production and Scaling

---

**Q: Is this project production-ready? What would you add?**

A: For a demo or internal tool, yes. For production serving real users:
1. Authentication (JWT or API keys via `Depends`)
2. Rate limiting (especially on voice and PDF upload endpoints)
3. Persistent vector store (ChromaDB or Pinecone instead of in-memory FAISS)
4. PostgreSQL instead of SQLite (for multi-instance deployments)
5. Structured logging (instead of `print()`) with correlation IDs per request
6. Request timeouts (Whisper and TTS can be slow — set `timeout=` on API calls)
7. Health check that validates OpenAI connectivity, not just server uptime
8. Tests (unit tests for services, integration tests for endpoints)
9. Background task queue (Celery or ARQ) for heavy operations like PDF ingestion

---

**Q: There's a Dockerfile in the project but it only has `FROM python:3.12`. What would a complete Dockerfile look like?**

A: A production-grade Dockerfile:

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy dependency manifest first (Docker layer caching)
COPY ../pyproject.toml uv.lock ./

# Install dependencies into the system Python (no venv needed in Docker)
RUN uv sync --frozen --no-dev

# Copy application code
COPY .. .

# Expose the port
EXPOSE 8000

# Run with uvicorn, single worker in container (scale by running more containers)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```
Key choices: `python:3.12-slim` (smaller image), copy `pyproject.toml` before code
(so dependency layer is cached when only code changes), `--frozen` (fail if
`uv.lock` is out of date), no `--reload` in production.

---

**Q: This project runs as a single process. How would you scale it to handle 1000 concurrent users?**

A: Horizontal scaling — run multiple instances behind a load balancer. But first, fix
the shared state problems:
1. SQLite doesn't support concurrent writes from multiple processes — switch to
   PostgreSQL with `PostgresSaver`
2. FAISS is in-memory per process — switch to a shared vector store (Pinecone, or a
   single ChromaDB instance)
3. Use Redis for any other shared state (rate limiting counts, session data)

Once state is externalised, deploy multiple container instances. Each instance is
stateless and can handle any request. Kubernetes with horizontal pod autoscaling (HPA)
would scale instances based on CPU/memory.

---

**Q: What would you monitor in production for this service?**

A: Four categories:
1. **Latency** — p50, p95, p99 response times per endpoint, broken out by phase
   (Whisper time, agent time, TTS time)
2. **Error rates** — `5xx` errors (server crashes), `4xx` errors (client mistakes),
   OpenAI API errors (rate limits, timeouts)
3. **Business metrics** — requests per endpoint per day, average conversation length,
   PDF uploads per day
4. **Resource usage** — RAM (FAISS grows with each upload), CPU (embedding is CPU-bound)

Tools: Prometheus + Grafana for metrics, structured logging sent to Datadog or
Elasticsearch.

---

**Q: How would you handle OpenAI API rate limits gracefully?**

A: Add retry logic with exponential backoff using the `tenacity` library:
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
def invoke_with_retry(self, message, thread_id):
    return self.invoke(message, thread_id)
```
Also: use `asyncio.Semaphore` to limit concurrent OpenAI calls, queue requests during
rate limit periods, and return a clear user-facing error message (not a raw API error)
when retries are exhausted.

---

*Last updated after the full project was completed and verified working end-to-end.*
*Reference file: `E:\Fastapi_voicebot` — every answer is grounded in actual code.*
