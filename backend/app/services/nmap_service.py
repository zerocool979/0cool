import asyncio
import subprocess
import shlex
import uuid
import re
import logging
from datetime import datetime
from typing import Dict, Callable, Optional, AsyncGenerator
from pathlib import Path

from app.models.nmap_models import (
    NmapScanResult, ScanStatus, NmapRunStats, HostInfo
)
from app.utils.xml_parser import parse_nmap_xml
from app.core.exceptions import NmapExecutionError, InvalidCommandError
from app.core.config import settings

logger = logging.getLogger(__name__)

# In-memory scan store (production: use Redis)
_scan_store: Dict[str, NmapScanResult] = {}
_scan_callbacks: Dict[str, list[Callable]] = {}


ALLOWED_NMAP_FLAGS = {
    "-sS", "-sT", "-sU", "-sN", "-sF", "-sX", "-sA", "-sW",
    "-sV", "-sC", "-O", "-A", "-p", "-F", "--top-ports",
    "--open", "-v", "-vv", "--reason", "--script",
    "-T0", "-T1", "-T2", "-T3", "-T4", "-T5",
    "-Pn", "-n", "--traceroute", "-oX", "-oN",
    "--min-rate", "--max-retries", "--host-timeout",
    "--exclude", "--excludefile",
}

BLOCKED_PATTERNS = [
    r"[;&|`$]",          # Shell injection chars
    r"\.\./",            # Path traversal
    r"--script-args",    # Potentially dangerous script args
    r"-oG",              # Grepable output to arbitrary files
    r"--send-eth",       # Raw ethernet (requires special perms)
]


def validate_nmap_command(command: str) -> tuple[bool, str]:
    """Validate nmap command for safety and correctness."""
    command = command.strip()

    # Must start with 'nmap'
    if not command.lower().startswith("nmap"):
        return False, "Command must start with 'nmap'"

    # Check for shell injection patterns
    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, command):
            return False, f"Potentially dangerous pattern detected: {pattern}"

    # Parse and validate tokens
    try:
        tokens = shlex.split(command)
    except ValueError as e:
        return False, f"Invalid command syntax: {e}"

    if len(tokens) < 2:
        return False, "Command too short — missing target"

    return True, "OK"


def _build_xml_command(original_command: str, xml_output_path: str) -> str:
    """Add XML output flag to nmap command."""
    command = original_command.strip()
    if "-oX" not in command:
        command = f"{command} -oX {xml_output_path}"
    return command


async def run_nmap_scan(
    command: str,
    on_progress: Optional[Callable] = None
) -> str:
    """Run an nmap scan and return scan_id."""
    valid, msg = validate_nmap_command(command)
    if not valid:
        raise InvalidCommandError(msg)

    scan_id = str(uuid.uuid4())
    xml_output_path = f"/tmp/nmap_scan_{scan_id}.xml"

    scan_result = NmapScanResult(
        scan_id=scan_id,
        command=command,
        start_time=datetime.now(),
        status=ScanStatus.RUNNING,
    )
    _scan_store[scan_id] = scan_result

    if on_progress:
        _scan_callbacks[scan_id] = [on_progress]

    # Run in background
    asyncio.create_task(_execute_scan(scan_id, command, xml_output_path))
    return scan_id


async def _execute_scan(
    scan_id: str,
    command: str,
    xml_output_path: str
) -> None:
    """Execute nmap scan asynchronously."""
    scan = _scan_store.get(scan_id)
    if not scan:
        return

    full_command = _build_xml_command(command, xml_output_path)

    try:
        logger.info(f"Executing: {full_command}")
        process = await asyncio.create_subprocess_shell(
            full_command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout_lines = []
        stderr_lines = []

        # Stream stdout
        async def read_stream(stream, lines_list):
            async for line in stream:
                decoded = line.decode("utf-8", errors="replace").strip()
                if decoded:
                    lines_list.append(decoded)
                    await _notify_progress(scan_id, decoded)

        await asyncio.gather(
            read_stream(process.stdout, stdout_lines),
            read_stream(process.stderr, stderr_lines)
        )

        return_code = await asyncio.wait_for(
            process.wait(),
            timeout=settings.NMAP_TIMEOUT
        )

        raw_output = "\n".join(stdout_lines)
        if stderr_lines:
            raw_output += "\n\nSTDERR:\n" + "\n".join(stderr_lines)

        scan.raw_output = raw_output

        if return_code != 0 and not Path(xml_output_path).exists():
            raise NmapExecutionError(f"Nmap exited with code {return_code}: {' '.join(stderr_lines)}")

        # Parse XML output
        xml_path = Path(xml_output_path)
        if xml_path.exists():
            xml_content = xml_path.read_text()
            hosts, run_stats = parse_nmap_xml(xml_content)
            scan.hosts = hosts
            scan.run_stats = run_stats
            xml_path.unlink(missing_ok=True)  # cleanup
        else:
            logger.warning(f"No XML output for scan {scan_id}")

        scan.status = ScanStatus.COMPLETED
        scan.end_time = datetime.now()
        logger.info(f"Scan {scan_id} completed: {len(scan.hosts)} hosts")

    except asyncio.TimeoutError:
        scan.status = ScanStatus.FAILED
        scan.error_message = "Scan timed out"
        logger.error(f"Scan {scan_id} timed out")
    except Exception as e:
        scan.status = ScanStatus.FAILED
        scan.error_message = str(e)
        logger.error(f"Scan {scan_id} failed: {e}", exc_info=True)
    finally:
        scan.end_time = scan.end_time or datetime.now()
        await _notify_complete(scan_id)


async def _notify_progress(scan_id: str, line: str) -> None:
    callbacks = _scan_callbacks.get(scan_id, [])
    for cb in callbacks:
        try:
            await cb({"type": "progress", "scan_id": scan_id, "line": line})
        except Exception:
            pass


async def _notify_complete(scan_id: str) -> None:
    scan = _scan_store.get(scan_id)
    if not scan:
        return
    callbacks = _scan_callbacks.get(scan_id, [])
    for cb in callbacks:
        try:
            await cb({"type": "complete", "scan_id": scan_id, "status": scan.status.value})
        except Exception:
            pass
    _scan_callbacks.pop(scan_id, None)


def get_scan(scan_id: str) -> Optional[NmapScanResult]:
    return _scan_store.get(scan_id)


def register_callback(scan_id: str, callback: Callable) -> None:
    if scan_id not in _scan_callbacks:
        _scan_callbacks[scan_id] = []
    _scan_callbacks[scan_id].append(callback)


def list_scans() -> list[NmapScanResult]:
    return list(_scan_store.values())
