"""
ai_provider.py — Hybrid AI Provider Router

Exposes a single unified interface identical to what ollama_service already
provides.  Callers (chat endpoint, websocket, nmap endpoint) import from here
instead of directly from ollama_service.  Zero changes needed in those callers
except swapping the import.

Provider selection order:
  1. Explicit `provider` field on the request  ("gemini" | "slm")
  2. DEFAULT_AI_PROVIDER setting (env var, default = "gemini")

Fallback chain:
  Gemini fails (no key / no internet) → auto-falls-back to SLM if Ollama is up.
"""

import logging
from typing import AsyncGenerator, Literal, Optional

from app.core.config import settings
from app.models.chat_models import ChatSession
from app.models.nmap_models import NmapScanResult, ScanAnalysis
from app.services import gemini_service, ollama_service

logger = logging.getLogger(__name__)

AIProvider = Literal["gemini", "slm"]


# ─── Public helpers ────────────────────────────────────────────────────────────

def resolve_provider(requested: Optional[str]) -> AIProvider:
    """Return the concrete provider to use for this request."""
    p = (requested or settings.DEFAULT_AI_PROVIDER).lower()
    if p not in ("gemini", "slm"):
        p = settings.DEFAULT_AI_PROVIDER
    return p  # type: ignore[return-value]


async def health() -> dict:
    """Return health status of both providers."""
    gemini_h = await gemini_service.check_gemini_health()
    ollama_h = await ollama_service.check_ollama_health()
    return {
        "default_provider": settings.DEFAULT_AI_PROVIDER,
        "gemini": gemini_h,
        "slm": ollama_h,
    }


# ─── Unified streaming chat ───────────────────────────────────────────────────

async def stream_chat(
    message: str,
    session_id: str,
    context: Optional[str] = None,
    provider: Optional[str] = None,
) -> AsyncGenerator[str, None]:
    """
    Stream AI response.  Transparently selects Gemini or Ollama.
    On Gemini failure auto-falls-back to SLM and yields a notice first.
    """
    chosen = resolve_provider(provider)

    if chosen == "gemini":
        # Try Gemini; catch hard failures and fall back to SLM
        try:
            had_output = False
            async for chunk in gemini_service.stream_chat(message, session_id, context):
                had_output = True
                yield chunk
            if had_output:
                return
        except Exception as e:
            logger.warning(f"Gemini stream failed ({e}), falling back to SLM")

        # Fallback notice
        yield "\n\n⚠️ **Gemini tidak tersedia** — beralih ke SLM lokal (Ollama).\n\n"
        async for chunk in ollama_service.stream_chat(message, session_id, context):
            yield chunk

    else:  # slm
        async for chunk in ollama_service.stream_chat(message, session_id, context):
            yield chunk


# ─── Unified scan analysis ────────────────────────────────────────────────────

async def analyze_scan_result(
    scan_result: NmapScanResult,
    provider: Optional[str] = None,
) -> ScanAnalysis:
    """
    Analyze scan with the chosen AI provider.
    Falls back to rule-based analysis if both providers fail.
    """
    chosen = resolve_provider(provider)

    if chosen == "gemini":
        try:
            return await gemini_service.analyze_scan_result(scan_result)
        except Exception as e:
            logger.warning(f"Gemini analysis failed ({e}), falling back to SLM")
        try:
            return await ollama_service.analyze_scan_result(scan_result)
        except Exception as e2:
            logger.warning(f"SLM analysis also failed ({e2}), using rule-based fallback")
    else:
        try:
            return await ollama_service.analyze_scan_result(scan_result)
        except Exception as e:
            logger.warning(f"SLM analysis failed ({e}), using rule-based fallback")

    # Rule-based fallback — always works, no AI required
    return _rule_based_analysis(scan_result)


def _rule_based_analysis(scan_result: NmapScanResult) -> ScanAnalysis:
    from app.services.ollama_service import (
        _assess_port_risks, _calculate_overall_risk,
        _generate_fallback_summary, _generate_fallback_recommendations,
        _generate_next_commands, _default_legal_notice,
    )
    port_risks = _assess_port_risks(scan_result)
    open_ports = sum(
        len([p for p in h.ports if p.state == "open"]) for h in scan_result.hosts
    )
    return ScanAnalysis(
        scan_id=scan_result.scan_id,
        summary=_generate_fallback_summary(scan_result),
        total_hosts=len(scan_result.hosts),
        open_ports_count=open_ports,
        risk_assessment=_calculate_overall_risk(port_risks),
        port_risks=port_risks,
        vulnerabilities=[],
        ai_analysis="(Analisis AI tidak tersedia — menggunakan penilaian berbasis aturan)",
        recommendations=_generate_fallback_recommendations(port_risks),
        next_commands=_generate_next_commands(scan_result),
        legal_notice=_default_legal_notice(),
    )


# ─── Session passthrough ──────────────────────────────────────────────────────

def get_session(session_id: str, provider: Optional[str] = None) -> Optional[ChatSession]:
    chosen = resolve_provider(provider)
    if chosen == "gemini":
        return gemini_service.get_session(session_id)
    return ollama_service.get_session(session_id)


def clear_session(session_id: str) -> None:
    """Remove session from both stores (user may have switched providers mid-convo)."""
    gemini_service._sessions.pop(session_id, None)
    ollama_service._sessions.pop(session_id, None)
