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