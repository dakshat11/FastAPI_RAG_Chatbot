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