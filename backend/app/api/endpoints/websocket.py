import asyncio
import json
import logging
import uuid
from typing import Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services import nmap_service, ollama_service
from app.models.nmap_models import ScanStatus, ScanRequest
from app.core.exceptions import InvalidCommandError

logger = logging.getLogger(__name__)
router = APIRouter(tags=["WebSocket"])

# Track active connections
_active_connections: Set[WebSocket] = set()


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        _active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        _active_connections.discard(websocket)

    async def send(self, websocket: WebSocket, data: dict):
        try:
            await websocket.send_json(data)
        except Exception:
            self.disconnect(websocket)


manager = ConnectionManager()


@router.websocket("/ws/scan")
async def websocket_scan(websocket: WebSocket):
    """WebSocket endpoint for real-time scan updates."""
    await manager.connect(websocket)
    scan_id = None

    try:
        await websocket.send_json({
            "type": "connected",
            "message": "WebSocket terhubung. Kirim perintah nmap untuk memulai scan."
        })

        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type", "scan")

            if msg_type == "scan":
                command = data.get("command", "").strip()
                if not command:
                    await manager.send(websocket, {
                        "type": "error",
                        "message": "Command tidak boleh kosong"
                    })
                    continue

                # Create progress callback
                async def on_progress(event: dict):
                    await manager.send(websocket, {
                        "type": "progress",
                        "scan_id": event.get("scan_id"),
                        "line": event.get("line", ""),
                        "status": event.get("status")
                    })

                try:
                    scan_id = await nmap_service.run_nmap_scan(command, on_progress)
                    await manager.send(websocket, {
                        "type": "scan_started",
                        "scan_id": scan_id,
                        "command": command,
                        "message": "Scan dimulai..."
                    })

                    # Poll for completion
                    while True:
                        await asyncio.sleep(1)
                        scan = nmap_service.get_scan(scan_id)
                        if not scan:
                            break

                        if scan.status == ScanStatus.COMPLETED:
                            await manager.send(websocket, {
                                "type": "scan_complete",
                                "scan_id": scan_id,
                                "hosts_count": len(scan.hosts),
                                "result": scan.model_dump(mode="json")
                            })

                            # Trigger AI analysis
                            await manager.send(websocket, {
                                "type": "analyzing",
                                "message": "Menganalisis hasil scan dengan AI..."
                            })
                            try:
                                analysis = await ollama_service.analyze_scan_result(scan)
                                await manager.send(websocket, {
                                    "type": "analysis_complete",
                                    "scan_id": scan_id,
                                    "analysis": analysis.model_dump(mode="json")
                                })
                            except Exception as e:
                                await manager.send(websocket, {
                                    "type": "analysis_error",
                                    "message": str(e)
                                })
                            break

                        elif scan.status == ScanStatus.FAILED:
                            await manager.send(websocket, {
                                "type": "scan_failed",
                                "scan_id": scan_id,
                                "error": scan.error_message
                            })
                            break

                except InvalidCommandError as e:
                    await manager.send(websocket, {
                        "type": "error",
                        "message": str(e)
                    })

            elif msg_type == "cancel":
                if scan_id:
                    scan = nmap_service.get_scan(scan_id)
                    if scan and scan.status == ScanStatus.RUNNING:
                        scan.status = ScanStatus.CANCELLED
                    await manager.send(websocket, {
                        "type": "cancelled",
                        "scan_id": scan_id
                    })

            elif msg_type == "ping":
                await manager.send(websocket, {"type": "pong"})

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info(f"WebSocket disconnected (scan_id: {scan_id})")
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        manager.disconnect(websocket)


@router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """WebSocket endpoint for real-time AI chat."""
    await manager.connect(websocket)
    session_id = str(uuid.uuid4())

    try:
        await websocket.send_json({
            "type": "connected",
            "session_id": session_id,
            "message": "Chat terhubung. Mulai percakapan Anda."
        })

        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type", "message")

            if msg_type == "message":
                message = data.get("content", "").strip()
                if not message:
                    continue

                await manager.send(websocket, {
                    "type": "typing",
                    "session_id": session_id
                })

                # Stream AI response
                full_response = ""
                async for chunk in ollama_service.stream_chat(
                    message,
                    session_id,
                    data.get("context")
                ):
                    full_response += chunk
                    await manager.send(websocket, {
                        "type": "chunk",
                        "session_id": session_id,
                        "content": chunk
                    })

                await manager.send(websocket, {
                    "type": "message_complete",
                    "session_id": session_id,
                    "full_content": full_response
                })

            elif msg_type == "ping":
                await manager.send(websocket, {"type": "pong"})

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"Chat WebSocket error: {e}")
        manager.disconnect(websocket)
