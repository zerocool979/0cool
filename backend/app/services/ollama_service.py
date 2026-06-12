import httpx
import json
import logging
from typing import AsyncGenerator, Optional, List
from datetime import datetime

from app.core.config import settings
from app.core.exceptions import OllamaConnectionError, OllamaModelNotFoundError
from app.models.chat_models import ChatMessage, MessageRole, ChatSession
from app.models.nmap_models import NmapScanResult, ScanAnalysis, PortRisk, RiskLevel

logger = logging.getLogger(__name__)

# In-memory session store (production: use Redis)
_sessions: dict[str, ChatSession] = {}

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
- Struktur jawaban: Analisis → Risiko → Mitigasi → Perintah Lanjutan

Selalu ingatkan pengguna untuk hanya melakukan scanning pada jaringan yang mereka miliki izin akses."""


HIGH_RISK_PORTS = {
    21: ("FTP", "high", "FTP tidak terenkripsi, rentan sniffing"),
    22: ("SSH", "medium", "Pastikan menggunakan key-based auth, disable password auth"),
    23: ("Telnet", "critical", "Telnet tidak terenkripsi sama sekali, ganti dengan SSH"),
    25: ("SMTP", "medium", "Potensi open relay, pastikan autentikasi aktif"),
    80: ("HTTP", "medium", "Tidak terenkripsi, pertimbangkan redirect ke HTTPS"),
    110: ("POP3", "high", "Email tidak terenkripsi"),
    135: ("RPC", "high", "Windows RPC, sering dieksploitasi"),
    139: ("NetBIOS", "high", "Windows file sharing, potensi eksploitasi"),
    143: ("IMAP", "high", "Email tidak terenkripsi"),
    443: ("HTTPS", "low", "Pastikan sertifikat valid dan TLS terbaru"),
    445: ("SMB", "critical", "Rentan EternalBlue/WannaCry, patch segera"),
    1433: ("MSSQL", "high", "Database SQL Server terbuka"),
    1521: ("Oracle DB", "high", "Database Oracle terbuka"),
    3306: ("MySQL", "high", "Database MySQL terbuka ke publik"),
    3389: ("RDP", "critical", "Remote Desktop terbuka, target utama brute force"),
    5432: ("PostgreSQL", "high", "Database PostgreSQL terbuka"),
    5900: ("VNC", "critical", "VNC sering tanpa enkripsi"),
    6379: ("Redis", "critical", "Redis biasanya tanpa autentikasi"),
    8080: ("HTTP-Alt", "medium", "Web server alternatif"),
    8443: ("HTTPS-Alt", "low", "HTTPS alternatif"),
    27017: ("MongoDB", "critical", "MongoDB sering tanpa autentikasi"),
}


async def check_ollama_health() -> dict:
    """Check if Ollama is running and model is available."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
            if resp.status_code == 200:
                data = resp.json()
                models = [m["name"] for m in data.get("models", [])]
                return {
                    "status": "ok",
                    "models": models,
                    "target_model": settings.OLLAMA_MODEL,
                    "model_available": any(
                        settings.OLLAMA_MODEL in m for m in models
                    )
                }
    except Exception as e:
        logger.warning(f"Ollama health check failed: {e}")
    return {"status": "error", "message": "Cannot connect to Ollama"}


async def stream_chat(
    message: str,
    session_id: str,
    context: Optional[str] = None
) -> AsyncGenerator[str, None]:
    """Stream chat response from Ollama."""
    session = _get_or_create_session(session_id)

    # Add user message
    session.messages.append(ChatMessage(role=MessageRole.USER, content=message))
    session.updated_at = datetime.now()

    # Build messages for API
    api_messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    if context:
        api_messages.append({
            "role": "system",
            "content": f"Konteks scan terkini:\n{context}"
        })

    for msg in session.messages[-20:]:  # Keep last 20 messages for context
        api_messages.append({
            "role": msg.role.value,
            "content": msg.content
        })

    full_response = ""

    try:
        async with httpx.AsyncClient(timeout=settings.OLLAMA_TIMEOUT) as client:
            async with client.stream(
                "POST",
                f"{settings.OLLAMA_BASE_URL}/api/chat",
                json={
                    "model": settings.OLLAMA_MODEL,
                    "messages": api_messages,
                    "stream": True,
                    "options": {
                        "temperature": 0.3,
                        "top_p": 0.9,
                        "num_predict": 2048,
                    }
                }
            ) as response:
                if response.status_code != 200:
                    raise OllamaConnectionError(f"HTTP {response.status_code}")

                async for line in response.aiter_lines():
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        if "message" in data and "content" in data["message"]:
                            chunk = data["message"]["content"]
                            full_response += chunk
                            yield chunk
                        if data.get("done"):
                            break
                    except json.JSONDecodeError:
                        continue

    except httpx.ConnectError:
        error_msg = "⚠️ Tidak dapat terhubung ke Ollama. Pastikan Ollama berjalan di localhost:11434"
        yield error_msg
        full_response = error_msg
    except Exception as e:
        error_msg = f"⚠️ Error: {str(e)}"
        yield error_msg
        full_response = error_msg
    finally:
        # Store assistant response
        if full_response:
            session.messages.append(
                ChatMessage(role=MessageRole.ASSISTANT, content=full_response)
            )


async def analyze_scan_result(scan_result: NmapScanResult) -> ScanAnalysis:
    """Use AI to analyze nmap scan results."""
    # Build structured analysis prompt
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

    try:
        async with httpx.AsyncClient(timeout=settings.OLLAMA_TIMEOUT) as client:
            resp = await client.post(
                f"{settings.OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": settings.OLLAMA_MODEL,
                    "prompt": prompt,
                    "system": SYSTEM_PROMPT,
                    "stream": False,
                    "options": {"temperature": 0.1, "num_predict": 2048}
                }
            )

            if resp.status_code == 200:
                data = resp.json()
                response_text = data.get("response", "")
                # Extract JSON from response
                ai_data = _parse_json_response(response_text)
            else:
                ai_data = {}

    except Exception as e:
        logger.error(f"AI analysis failed: {e}")
        ai_data = {}

    # Build port risks (rule-based + AI enrichment)
    port_risks = _assess_port_risks(scan_result)

    # Determine overall risk
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

    analysis = ScanAnalysis(
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

    return analysis


def _build_scan_summary(scan_result: NmapScanResult) -> str:
    lines = [f"Command: {scan_result.command}"]
    lines.append(f"Total hosts: {len(scan_result.hosts)}")
    lines.append(f"Duration: {scan_result.run_stats.elapsed:.1f}s")
    lines.append("")

    for host in scan_result.hosts:
        lines.append(f"Host: {host.address} ({host.hostname or 'no hostname'})")
        lines.append(f"  Status: {host.status}")

        if host.os_matches:
            lines.append(f"  OS: {host.os_matches[0].name} ({host.os_matches[0].accuracy}%)")

        open_ports = [p for p in host.ports if p.state == "open"]
        lines.append(f"  Open ports ({len(open_ports)}):")
        for port in open_ports[:20]:  # Limit to avoid token overflow
            svc = port.service
            service_str = f"{svc.name}"
            if svc.product:
                service_str += f" ({svc.product} {svc.version})"
            lines.append(f"    {port.port}/{port.protocol}: {service_str}")

    return "\n".join(lines)


def _parse_json_response(text: str) -> dict:
    """Extract JSON from AI response."""
    import re
    # Try to find JSON block
    json_match = re.search(r'\{.*\}', text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
    return {}


def _assess_port_risks(scan_result: NmapScanResult) -> list[PortRisk]:
    risks = []
    for host in scan_result.hosts:
        for port in host.ports:
            if port.state != "open":
                continue
            if port.port in HIGH_RISK_PORTS:
                service_name, risk_str, description = HIGH_RISK_PORTS[port.port]
                try:
                    risk_level = RiskLevel(risk_str)
                except ValueError:
                    risk_level = RiskLevel.MEDIUM

                risks.append(PortRisk(
                    port=port.port,
                    protocol=port.protocol,
                    service=port.service.name or service_name,
                    risk_level=risk_level,
                    description=description,
                    recommendation=_get_port_recommendation(port.port)
                ))
    return risks


def _get_port_recommendation(port: int) -> str:
    recommendations = {
        21: "Nonaktifkan FTP, gunakan SFTP atau SCP sebagai gantinya",
        22: "Gunakan key-based authentication, disable root login, ubah port default",
        23: "Segera nonaktifkan Telnet, migrasi ke SSH",
        445: "Terapkan patch MS17-010, isolasi dari internet, gunakan firewall",
        3389: "Gunakan VPN sebelum RDP, aktifkan NLA, batasi IP yang diizinkan",
        3306: "Batasi akses ke localhost/IP tertentu, jangan expose ke publik",
        6379: "Aktifkan autentikasi Redis, bind ke localhost saja",
        27017: "Aktifkan autentikasi MongoDB, gunakan firewall",
    }
    return recommendations.get(port, "Tinjau kebutuhan port ini, batasi akses dengan firewall")


def _calculate_overall_risk(port_risks: list[PortRisk]) -> RiskLevel:
    if not port_risks:
        return RiskLevel.INFO
    risk_order = [RiskLevel.CRITICAL, RiskLevel.HIGH, RiskLevel.MEDIUM, RiskLevel.LOW, RiskLevel.INFO]
    risk_counts = {r: 0 for r in risk_order}
    for pr in port_risks:
        risk_counts[pr.risk_level] += 1
    for risk in risk_order:
        if risk_counts[risk] > 0:
            return risk
    return RiskLevel.INFO


def _generate_fallback_summary(scan_result: NmapScanResult) -> str:
    hosts_up = len([h for h in scan_result.hosts if h.status == "up"])
    open_ports = sum(len([p for p in h.ports if p.state == "open"]) for h in scan_result.hosts)
    return f"Scan menemukan {hosts_up} host aktif dengan total {open_ports} port terbuka."


def _generate_fallback_recommendations(port_risks: list[PortRisk]) -> list[str]:
    recs = []
    critical = [pr for pr in port_risks if pr.risk_level == RiskLevel.CRITICAL]
    for pr in critical[:3]:
        recs.append(f"Port {pr.port} ({pr.service}): {pr.recommendation}")
    if not recs:
        recs.append("Tinjau semua port terbuka dan terapkan prinsip least privilege")
    return recs


def _generate_next_commands(scan_result: NmapScanResult) -> list[str]:
    commands = []
    for host in scan_result.hosts[:3]:
        commands.append(f"nmap -sV -sC -O {host.address}")
        commands.append(f"nmap --script vuln {host.address}")
        commands.append(f"nmap -sU --top-ports 100 {host.address}")
    return list(set(commands))[:5]


def _default_legal_notice() -> str:
    return """⚠️ PERHATIAN HUKUM: Pemindaian jaringan tanpa izin eksplisit dari pemilik sistem 
dapat melanggar Pasal 30 UU ITE No. 11 Tahun 2008 tentang Informasi dan Transaksi Elektronik, 
dengan ancaman pidana penjara dan/atau denda. Pastikan Anda memiliki izin tertulis sebelum 
melakukan penetration testing atau network scanning pada jaringan yang bukan milik Anda."""


def _get_or_create_session(session_id: str) -> ChatSession:
    if session_id not in _sessions:
        _sessions[session_id] = ChatSession(session_id=session_id)
    return _sessions[session_id]


def get_session(session_id: str) -> Optional[ChatSession]:
    return _sessions.get(session_id)
