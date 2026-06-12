import uuid
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
import logging

from app.models.chat_models import ChatRequest, ChatResponse, MessageRole
from app.services import ollama_service
from app.services.nmap_service import get_scan
from app.services.ollama_service import _build_scan_summary

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("/stream")
async def chat_stream(request: ChatRequest):
    """Stream chat response from AI model."""
    session_id = request.session_id or str(uuid.uuid4())

    # Build context from scan if provided
    context = request.context
    if request.scan_id and not context:
        scan = get_scan(request.scan_id)
        if scan:
            context = f"Konteks scan:\n{_build_scan_summary(scan)}"

    async def generate():
        yield f"data: {session_id}\n\n"  # Send session ID first
        async for chunk in ollama_service.stream_chat(
            request.message, session_id, context
        ):
            # SSE format
            chunk_escaped = chunk.replace("\n", "\\n")
            yield f"data: {chunk_escaped}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        }
    )


@router.post("/message", response_model=ChatResponse)
async def chat_message(request: ChatRequest):
    """Non-streaming chat endpoint."""
    session_id = request.session_id or str(uuid.uuid4())

    context = request.context
    if request.scan_id and not context:
        scan = get_scan(request.scan_id)
        if scan:
            context = f"Konteks scan:\n{_build_scan_summary(scan)}"

    full_response = ""
    async for chunk in ollama_service.stream_chat(request.message, session_id, context):
        full_response += chunk

    return ChatResponse(
        session_id=session_id,
        message=full_response,
        role=MessageRole.ASSISTANT
    )


@router.get("/session/{session_id}")
async def get_session(session_id: str):
    """Get chat session history."""
    session = ollama_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session tidak ditemukan")
    return session


@router.delete("/session/{session_id}")
async def clear_session(session_id: str):
    """Clear chat session."""
    from app.services.ollama_service import _sessions
    if session_id in _sessions:
        del _sessions[session_id]
    return {"message": "Session dihapus"}


@router.get("/health")
async def check_ai_health():
    """Check Ollama/AI model health."""
    return await ollama_service.check_ollama_health()
