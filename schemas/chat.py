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