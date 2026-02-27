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