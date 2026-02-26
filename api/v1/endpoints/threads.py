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