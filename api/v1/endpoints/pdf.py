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