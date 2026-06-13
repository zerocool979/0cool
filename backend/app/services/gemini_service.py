"""
GeminiService — Google Gemini provider.
Mirrors the public interface of ollama_service so the provider router
can call either service transparently.
"""

import json
import logging
from typing import AsyncGenerator, Optional
from datetime import datetime

import httpx

from app.core.config import settings
from app.models.chat_models import ChatMessage, MessageRole, ChatSession
from app.models.nmap_models import NmapScanResult, ScanAnalysis, PortRisk, RiskLevel

logger = logging.getLogger(__name__)

# Session store shared with ollama_service namespace via provider router
_sessions: dict[str, ChatSession] = {}

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"

SYSTEM_PROMPT = """Anda adalah asisten keamanan jaringan yang ahli dalam analisis Nmap dan hukum keamanan siber Indonesia.

Kemampuan Anda:
1. Menganalisis hasil scan Nmap secara mendalam
2. Mengidentifikasi port dan layanan berisiko tinggi
3. Memberikan saran mitigasi keamanan yang actionable
4. Menjelaskan implikasi hukum berdasarkan UU ITE Indonesia
5. Merekomendasikan perintah Nmap lanjutan yang relevan

Panduan Hukum (UU ITE No. 11 Tahun 2008 & Perubahannya):
- Pasal 30: Akses ilegal ke sistem komputer orang lain adalah tindak pidana
- Pastikan pengguna memiliki izin eksplisit sebelum scanning
- Scanning tanpa izin dapat dikenakan sanksi pidana

Format respons Anda:
- Gunakan bahasa Indonesia yang jelas dan profesional
- Sertakan contoh kode/command jika relevan
- Selalu cantumkan disclaimer hukum untuk aktivitas scanning
- Struktur jawaban: Analisis → Risiko → Mitigasi → Perintah Lanjutan"""


# ─── Health check ─────────────────────────────────────────────────────────────

async def check_gemini_health() -> dict:
    """Verify Gemini API key is valid by listing models."""
    if not settings.GEMINI_API_KEY:
        return {"status": "error", "message": "GEMINI_API_KEY belum dikonfigurasi"}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{GEMINI_API_BASE}/models",
                params={"key": settings.GEMINI_API_KEY},
            )
            if resp.status_code == 200:
                models = [m["name"] for m in resp.json().get("models", [])]
                return {
                    "status": "ok",
                    "provider": "gemini",
                    "model": settings.GEMINI_MODEL,
                    "models": models[:5],
                }
            return {"status": "error", "message": f"HTTP {resp.status_code}: {resp.text[:120]}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ─── Streaming chat ────────────────────────────────────────────────────────────

async def stream_chat(
    message: str,
    session_id: str,
    context: Optional[str] = None,
) -> AsyncGenerator[str, None]:
    """Stream response from Gemini using Server-Sent Events."""
    if not settings.GEMINI_API_KEY:
        yield "⚠️ Gemini API key belum dikonfigurasi. Tambahkan `GEMINI_API_KEY` di file `.env` atau gunakan mode SLM (offline)."
        return

    session = _get_or_create_session(session_id)

    # Build Gemini contents array (history + current message)
    contents = _build_contents(session, message, context)

    session.messages.append(ChatMessage(role=MessageRole.USER, content=message))
    session.updated_at = datetime.now()

    url = (
        f"{GEMINI_API_BASE}/models/{settings.GEMINI_MODEL}"
        f":streamGenerateContent?alt=sse&key={settings.GEMINI_API_KEY}"
    )

    payload = {
        "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": contents,
        "generationConfig": {
            "temperature": 0.3,
            "topP": 0.9,
            "maxOutputTokens": 2048,
        },
        "safetySettings": [
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_ONLY_HIGH"},
        ],
    }

    full_response = ""
    try:
        async with httpx.AsyncClient(timeout=settings.GEMINI_TIMEOUT) as client:
            async with client.stream("POST", url, json=payload) as resp:
                if resp.status_code != 200:
                    body = await resp.aread()
                    err = json.loads(body).get("error", {}).get("message", resp.status_code)
                    yield f"⚠️ Gemini error: {err}"
                    return

                async for line in resp.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    raw = line[5:].strip()
                    if not raw or raw == "[DONE]":
                        continue
                    try:
                        data = json.loads(raw)
                        for part in (
                            data.get("candidates", [{}])[0]
                            .get("content", {})
                            .get("parts", [])
                        ):
                            chunk = part.get("text", "")
                            if chunk:
                                full_response += chunk
                                yield chunk
                    except (json.JSONDecodeError, IndexError, KeyError):
                        continue

    except httpx.ConnectError:
        msg = "⚠️ Tidak dapat terhubung ke Gemini API. Periksa koneksi internet atau gunakan mode SLM (offline)."
        yield msg
        full_response = msg
    except Exception as e:
        msg = f"⚠️ Gemini error: {e}"
        yield msg
        full_response = msg
    finally:
        if full_response:
            session.messages.append(
                ChatMessage(role=MessageRole.ASSISTANT, content=full_response)
            )


# ─── Scan analysis ─────────────────────────────────────────────────────────────

async def analyze_scan_result(scan_result: NmapScanResult) -> ScanAnalysis:
    """Use Gemini to analyze nmap scan results. Falls back to rule-based analysis."""
    from app.services.ollama_service import (
        _build_scan_summary, _assess_port_risks, _calculate_overall_risk,
        _generate_fallback_summary, _generate_fallback_recommendations,
        _generate_next_commands, _default_legal_notice, _parse_json_response,
        HIGH_RISK_PORTS,
    )

    scan_summary = _build_scan_summary(scan_result)

    prompt = f"""Analisis hasil scan Nmap berikut secara komprehensif:

{scan_summary}

Berikan analisis dalam format JSON dengan struktur:
{{
    "summary": "ringkasan eksekutif dalam 2-3 kalimat",
    "risk_assessment": "critical/high/medium/low/info",
    "vulnerabilities": ["kerentanan 1", "kerentanan 2"],
    "ai_analysis": "analisis mendalam dalam bahasa Indonesia",
    "recommendations": ["saran 1", "saran 2", "saran 3"],
    "next_commands": ["nmap command lanjutan 1", "nmap command lanjutan 2"],
    "legal_notice": "catatan hukum UU ITE yang relevan"
}}

Pastikan respons HANYA berupa JSON valid, tidak ada teks tambahan."""

    ai_data: dict = {}
    if settings.GEMINI_API_KEY:
        try:
            url = (
                f"{GEMINI_API_BASE}/models/{settings.GEMINI_MODEL}"
                f":generateContent?key={settings.GEMINI_API_KEY}"
            )
            payload = {
                "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.1, "maxOutputTokens": 2048},
            }
            async with httpx.AsyncClient(timeout=settings.GEMINI_TIMEOUT) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code == 200:
                    text = (
                        resp.json()
                        .get("candidates", [{}])[0]
                        .get("content", {})
                        .get("parts", [{}])[0]
                        .get("text", "")
                    )
                    ai_data = _parse_json_response(text)
        except Exception as e:
            logger.warning(f"Gemini analysis failed, using rule-based fallback: {e}")

    port_risks = _assess_port_risks(scan_result)
    overall_risk = _calculate_overall_risk(port_risks)
    if ai_data.get("risk_assessment"):
        try:
            overall_risk = RiskLevel(ai_data["risk_assessment"])
        except ValueError:
            pass

    open_ports = sum(
        len([p for p in h.ports if p.state == "open"])
        for h in scan_result.hosts
    )

    return ScanAnalysis(
        scan_id=scan_result.scan_id,
        summary=ai_data.get("summary", _generate_fallback_summary(scan_result)),
        total_hosts=len(scan_result.hosts),
        open_ports_count=open_ports,
        risk_assessment=overall_risk,
        port_risks=port_risks,
        vulnerabilities=ai_data.get("vulnerabilities", []),
        ai_analysis=ai_data.get("ai_analysis", ""),
        recommendations=ai_data.get("recommendations", _generate_fallback_recommendations(port_risks)),
        next_commands=ai_data.get("next_commands", _generate_next_commands(scan_result)),
        legal_notice=ai_data.get("legal_notice", _default_legal_notice()),
    )


# ─── Session helpers ───────────────────────────────────────────────────────────

def get_session(session_id: str) -> Optional[ChatSession]:
    return _sessions.get(session_id)


def _get_or_create_session(session_id: str) -> ChatSession:
    if session_id not in _sessions:
        _sessions[session_id] = ChatSession(session_id=session_id)
    return _sessions[session_id]


def _build_contents(
    session: ChatSession,
    new_message: str,
    context: Optional[str],
) -> list:
    """Convert session history → Gemini `contents` array."""
    contents = []

    # Inject scan context as a leading user→model exchange so Gemini
    # treats it as established fact, not a user instruction.
    if context:
        contents.append({
            "role": "user",
            "parts": [{"text": f"Berikut adalah konteks scan yang sedang dianalisis:\n{context}"}],
        })
        contents.append({
            "role": "model",
            "parts": [{"text": "Baik, saya sudah memahami konteks scan tersebut. Silakan ajukan pertanyaan Anda."}],
        })

    # Rolling history (last 20 pairs → 40 turns)
    for msg in session.messages[-40:]:
        role = "model" if msg.role == MessageRole.ASSISTANT else "user"
        contents.append({"role": role, "parts": [{"text": msg.content}]})

    # Current user message
    contents.append({"role": "user", "parts": [{"text": new_message}]})
    return contents
