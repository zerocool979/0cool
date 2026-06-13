import uuid
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
import logging

from app.models.chat_models import ChatRequest, ChatResponse, MessageRole
from app.services import ai_provider
from app.services.nmap_service import get_scan
from app.services.ollama_service import _build_scan_summary

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["Chat"])


def _build_context(request: ChatRequest) -> str | None:
    """Resolve scan context from request."""
    if request.context:
        return request.context
    if request.scan_id:
        scan = get_scan(request.scan_id)
        if scan:
            return f"Konteks scan:\n{_build_scan_summary(scan)}"
    return None


@router.post("/stream")
async def chat_stream(request: ChatRequest):
    """
    Stream AI response via SSE.
    Header `X-AI-Provider` in the response tells the client which provider was used.
    """
    session_id = request.session_id or str(uuid.uuid4())
    context = _build_context(request)
    provider = request.provider  # None → uses DEFAULT_AI_PROVIDER

    async def generate():
        # First chunk: session_id
        yield f"data: {session_id}\n\n"
        async for chunk in ai_provider.stream_chat(
            request.message, session_id, context, provider
        ):
            yield f"data: {chunk.replace(chr(10), chr(92) + 'n')}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "X-AI-Provider": ai_provider.resolve_provider(provider),
        },
    )


@router.post("/message", response_model=ChatResponse)
async def chat_message(request: ChatRequest):
    """Non-streaming chat — collects full response before returning."""
    session_id = request.session_id or str(uuid.uuid4())
    context = _build_context(request)
    provider = request.provider

    full_response = ""
    async for chunk in ai_provider.stream_chat(
        request.message, session_id, context, provider
    ):
        full_response += chunk

    return ChatResponse(
        session_id=session_id,
        message=full_response,
        role=MessageRole.ASSISTANT,
    )


@router.get("/session/{session_id}")
async def get_session(session_id: str, provider: str | None = None):
    """Get session history (provider-aware)."""
    session = ai_provider.get_session(session_id, provider)
    if not session:
        raise HTTPException(status_code=404, detail="Session tidak ditemukan")
    return session


@router.delete("/session/{session_id}")
async def clear_session(session_id: str):
    """Clear session from all provider stores."""
    ai_provider.clear_session(session_id)
    return {"message": "Session dihapus"}


@router.get("/health")
async def check_ai_health():
    """Return health of all AI providers."""
    return await ai_provider.health()


@router.get("/providers")
async def list_providers():
    """Describe available AI providers and current default."""
    from app.core.config import settings
    return {
        "default": settings.DEFAULT_AI_PROVIDER,
        "available": [
            {
                "id": "gemini",
                "name": "Google Gemini",
                "model": settings.GEMINI_MODEL,
                "requires_internet": True,
                "requires_api_key": True,
                "api_key_set": bool(settings.GEMINI_API_KEY),
            },
            {
                "id": "slm",
                "name": "Local SLM (Ollama)",
                "model": settings.OLLAMA_MODEL,
                "requires_internet": False,
                "requires_api_key": False,
                "ollama_url": settings.OLLAMA_BASE_URL,
            },
        ],
    }
