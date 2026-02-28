# api/v1/endpoints/voice.py
# Voice chat endpoint.
# Accepts audio, returns audio.
# Internally identical to the text chat endpoint — same agent, same thread memory.
#
# Why StreamingResponse for audio?
# We have raw MP3 bytes in memory and need to send them to the client as a file download.
# StreamingResponse lets us stream bytes from a BytesIO buffer without writing to disk.
# The media_type="audio/mpeg" tells the client how to handle the bytes.
#
# Why no response_model=?
# response_model is for JSON responses. When returning binary data (audio, images, files),
# you use Response subclasses directly (StreamingResponse, FileResponse) and skip response_model.

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi.responses import Response

from services.agent_service import agent_service
from services.voice_service import voice_service

router = APIRouter(prefix="/voice", tags=["voice"])


def _safe_header(value: str, max_len: int = 500) -> str:
    """
    Sanitize a string for use as an HTTP header value.

    Two things kill HTTP headers:
      1. Newlines (\n, \r\n, \r) — protocol delimiters in HTTP/1.1.
         Uvicorn raises RuntimeError: Invalid HTTP header value.
      2. Characters outside Latin-1 (ISO-8859-1, code points 0-255).
         HTTP/1.1 headers must be Latin-1 encodable. Unicode characters like
         curly quotes (\u2018 \u2019), em dashes (\u2014), ellipsis (\u2026)
         that LLMs commonly produce cause:
         UnicodeEncodeError: 'latin-1' codec can't encode character ...

    Fix: strip newlines first, then encode to Latin-1 with replace so any
    character outside the 0-255 range becomes '?'.
    """
    # Step 1 — remove newline variants (\r\n must come before \n)
    cleaned = value.replace("\r\n", " ").replace("\n", " ").replace("\r", " ")
    # Step 2 — drop any character that can't be encoded in Latin-1
    cleaned = cleaned.encode("latin-1", errors="replace").decode("latin-1")
    return cleaned[:max_len]


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
      5. Stream MP3 back to client

    The thread_id is shared with the text /chat endpoint.
    A conversation that started over text can continue over voice and vice versa.

    Call:  POST /api/v1/voice/chat?thread_id=my-thread
    Body:  multipart/form-data, key='file', value=audio file

    Response:  audio/mpeg binary stream
    Headers:   X-Transcript  — what was heard (useful for displaying in UI)
               X-Reply-Text  — text of the agent's reply (useful for subtitles)
               X-Thread-Id   — echoes the thread_id
    """
    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio file received.")

    try:
        # Step 1: Speech → Text
        # Whisper handles accents, background noise, and multiple languages automatically
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
        # This is EXACTLY the same call as the text /chat endpoint.
        # The voice layer is transparent to the agent.
        reply_text = agent_service.invoke(message=transcript, thread_id=thread_id)


        # Step 3: Text → Audio
        audio_response_bytes = voice_service.synthesise(text=reply_text)

        # Step 4: Return MP3 bytes directly to client.
        #
        # Why Response and NOT StreamingResponse?
        # StreamingResponse iterates over BytesIO line-by-line (splitting on \n).
        # MP3 is binary data — it contains 0x0A bytes (the \n byte value) throughout.
        # Splitting on those corrupts the audio. The client receives broken bytes
        # that cannot be decoded as MP3, so playback and download both fail.
        #
        # Response(content=bytes) sends the entire byte buffer in one shot — no
        # iteration, no corruption. Since we already have all bytes in memory
        # (TTS returns them synchronously), there is no benefit to streaming anyway.
        #
        # Content-Disposition: attachment  → forces browser/Swagger to download the file
        # Content-Disposition: inline      → tells browser to try to play in-page
        #                                    (Swagger UI has no audio player, so nothing happens)
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
        raise  # Re-raise our own HTTP exceptions unchanged
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Voice pipeline failed: {str(e)}")


@router.post("/transcribe-only")
async def transcribe_only(
    file: UploadFile = File(..., description="Audio file to transcribe"),
):
    """
    Transcribe audio to text without sending it to the agent.
    Useful for testing Whisper in isolation.
    Returns JSON with the transcribed text.
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