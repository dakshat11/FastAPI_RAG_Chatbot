# main.py
# The FastAPI application entry point.
# This file stays small. Its only jobs:
#   1. Create the app
#   2. Register the router
#   3. Define startup/shutdown logic (lifespan)
#   4. Define global endpoints (health check)

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins for development
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)


app.include_router(api_router)


@app.get("/health", tags=["system"])
async def health_check():
    """Quick liveness check — confirms the server is running."""
    return {"status": "healthy", "version": "1.0.0"}

