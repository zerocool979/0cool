from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
import asyncio
import logging
from pathlib import Path

from app.models.nmap_models import (
    ScanRequest, ScanResponse, ScanStatusResponse, ScanStatus
)
from app.models.report_models import ExportFormat, ReportRequest
from app.services import nmap_service, ollama_service, report_service
from app.core.exceptions import InvalidCommandError, NmapSLMException

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/nmap", tags=["Nmap"])


@router.post("/scan", response_model=ScanResponse)
async def start_scan(request: ScanRequest):
    """Start an nmap scan. Returns scan_id immediately."""
    try:
        scan_id = await nmap_service.run_nmap_scan(request.command)
        return ScanResponse(
            scan_id=scan_id,
            status=ScanStatus.RUNNING,
            message="Scan dimulai. Gunakan /scan/{scan_id}/status untuk memantau."
        )
    except InvalidCommandError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except NmapSLMException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.get("/scan/{scan_id}/status", response_model=ScanStatusResponse)
async def get_scan_status(scan_id: str):
    """Get current scan status and result."""
    scan = nmap_service.get_scan(scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail=f"Scan {scan_id} tidak ditemukan")

    response = ScanStatusResponse(
        scan_id=scan_id,
        status=scan.status,
        result=scan if scan.status in (ScanStatus.COMPLETED, ScanStatus.FAILED) else None
    )

    if scan.status == ScanStatus.RUNNING:
        response.message = "Scan sedang berjalan..."
        response.progress = 0.5
    elif scan.status == ScanStatus.COMPLETED:
        response.message = f"Scan selesai: {len(scan.hosts)} host ditemukan"
        response.progress = 1.0
    elif scan.status == ScanStatus.FAILED:
        response.message = scan.error_message or "Scan gagal"
        response.progress = 0.0

    return response


@router.post("/scan/{scan_id}/analyze")
async def analyze_scan(scan_id: str):
    """Trigger AI analysis for a completed scan."""
    scan = nmap_service.get_scan(scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail=f"Scan {scan_id} tidak ditemukan")

    if scan.status != ScanStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail=f"Scan belum selesai. Status: {scan.status.value}"
        )

    try:
        analysis = await ollama_service.analyze_scan_result(scan)
        return analysis
    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Analisis gagal: {str(e)}")


@router.get("/scans")
async def list_scans():
    """List all scans."""
    scans = nmap_service.list_scans()
    return [
        {
            "scan_id": s.scan_id,
            "command": s.command,
            "status": s.status.value,
            "start_time": s.start_time.isoformat(),
            "hosts_count": len(s.hosts)
        }
        for s in sorted(scans, key=lambda x: x.start_time, reverse=True)
    ]


@router.post("/scan/{scan_id}/report")
async def generate_report(scan_id: str, request: ReportRequest):
    """Generate and download a report."""
    scan = nmap_service.get_scan(scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail=f"Scan {scan_id} tidak ditemukan")

    if scan.status != ScanStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Scan belum selesai")

    # Get analysis if available
    analysis = None
    if request.include_analysis:
        try:
            analysis = await ollama_service.analyze_scan_result(scan)
        except Exception as e:
            logger.warning(f"Could not generate analysis for report: {e}")

    try:
        report = report_service.generate_report(
            scan, analysis, request.format, request.include_raw
        )

        media_types = {
            ExportFormat.PDF: "application/pdf",
            ExportFormat.MARKDOWN: "text/markdown",
            ExportFormat.JSON: "application/json",
        }

        return FileResponse(
            path=report.file_path,
            filename=report.filename,
            media_type=media_types.get(request.format, "application/octet-stream")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/scan/{scan_id}")
async def delete_scan(scan_id: str):
    """Delete a scan from memory."""
    from app.services.nmap_service import _scan_store
    if scan_id not in _scan_store:
        raise HTTPException(status_code=404, detail="Scan tidak ditemukan")
    del _scan_store[scan_id]
    return {"message": f"Scan {scan_id} dihapus"}
