# api/v1/api.py
# The router aggregator. All endpoint routers are included here.
# This file is the only place that knows about all routes.
# Adding a new feature = adding one include_router() line here.

from fastapi import APIRouter

from api.v1.endpoints import chat, threads, pdf, voice, resume

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(chat.router)      # → /api/v1/chat/
api_router.include_router(threads.router)
api_router.include_router(pdf.router)
api_router.include_router(voice.router)
api_router.include_router(resume.router)