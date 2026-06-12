import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.core.config import settings
from app.core.exceptions import ReportGenerationError, ScanNotFoundError
from app.models.nmap_models import NmapScanResult, ScanAnalysis
from app.models.report_models import ExportFormat, ReportResponse

logger = logging.getLogger(__name__)


def _ensure_reports_dir() -> Path:
    reports_dir = Path(settings.REPORTS_DIR)
    reports_dir.mkdir(parents=True, exist_ok=True)
    return reports_dir


def generate_report(
    scan_result: NmapScanResult,
    analysis: Optional[ScanAnalysis],
    format: ExportFormat,
    include_raw: bool = True,
) -> ReportResponse:
    """Generate a report in the requested format."""
    reports_dir = _ensure_reports_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_filename = f"nmap_report_{scan_result.scan_id[:8]}_{timestamp}"

    try:
        if format == ExportFormat.PDF:
            filename = f"{base_filename}.pdf"
            file_path = reports_dir / filename
            _generate_pdf(scan_result, analysis, file_path, include_raw)

        elif format == ExportFormat.MARKDOWN:
            filename = f"{base_filename}.md"
            file_path = reports_dir / filename
            content = _generate_markdown(scan_result, analysis, include_raw)
            file_path.write_text(content, encoding="utf-8")

        elif format == ExportFormat.JSON:
            filename = f"{base_filename}.json"
            file_path = reports_dir / filename
            content = _generate_json(scan_result, analysis)
            file_path.write_text(content, encoding="utf-8")

        else:
            raise ReportGenerationError(f"Unsupported format: {format}")

        size = file_path.stat().st_size
        return ReportResponse(
            scan_id=scan_result.scan_id,
            format=format,
            filename=filename,
            file_path=str(file_path),
            size_bytes=size,
        )

    except Exception as e:
        logger.error(f"Report generation failed: {e}", exc_info=True)
        raise ReportGenerationError(str(e))


def _generate_markdown(
    scan: NmapScanResult,
    analysis: Optional[ScanAnalysis],
    include_raw: bool
) -> str:
    lines = []
    lines.append("# Laporan Scan Nmap")
    lines.append(f"\n**Scan ID:** `{scan.scan_id}`")
    lines.append(f"**Command:** `{scan.command}`")
    lines.append(f"**Waktu Mulai:** {scan.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    if scan.end_time:
        lines.append(f"**Waktu Selesai:** {scan.end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        elapsed = (scan.end_time - scan.start_time).total_seconds()
        lines.append(f"**Durasi:** {elapsed:.1f} detik")
    lines.append(f"**Status:** {scan.status.value}")
    lines.append(f"\n---\n")

    if analysis:
        lines.append("## Ringkasan Eksekutif")
        lines.append(f"\n{analysis.summary}\n")
        lines.append(f"- **Total Host:** {analysis.total_hosts}")
        lines.append(f"- **Port Terbuka:** {analysis.open_ports_count}")
        lines.append(f"- **Level Risiko:** {analysis.risk_assessment.upper()}")
        lines.append("")

        if analysis.legal_notice:
            lines.append("## ⚖️ Catatan Hukum")
            lines.append(f"\n{analysis.legal_notice}\n")

    lines.append("## Hasil Scan Per Host")
    for host in scan.hosts:
        lines.append(f"\n### 🖥️ Host: {host.address}")
        if host.hostname:
            lines.append(f"- **Hostname:** {host.hostname}")
        lines.append(f"- **Status:** {host.status}")
        if host.os_matches:
            lines.append(f"- **OS:** {host.os_matches[0].name} ({host.os_matches[0].accuracy}%)")

        open_ports = [p for p in host.ports if p.state == "open"]
        if open_ports:
            lines.append(f"\n#### Port Terbuka ({len(open_ports)})\n")
            lines.append("| Port | Protocol | Layanan | Versi |")
            lines.append("|------|----------|---------|-------|")
            for port in open_ports:
                svc = port.service
                version = f"{svc.product} {svc.version}".strip() or "-"
                lines.append(f"| {port.port} | {port.protocol} | {svc.name or '-'} | {version} |")

    if analysis:
        if analysis.port_risks:
            lines.append("\n## 🚨 Penilaian Risiko Port\n")
            lines.append("| Port | Layanan | Level Risiko | Deskripsi |")
            lines.append("|------|---------|-------------|-----------|")
            for risk in sorted(analysis.port_risks, key=lambda x: ["critical","high","medium","low","info"].index(x.risk_level.value)):
                icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢", "info": "ℹ️"}.get(risk.risk_level.value, "")
                lines.append(f"| {risk.port} | {risk.service} | {icon} {risk.risk_level.upper()} | {risk.description} |")

        if analysis.vulnerabilities:
            lines.append("\n## 🔍 Kerentanan Teridentifikasi\n")
            for vuln in analysis.vulnerabilities:
                lines.append(f"- {vuln}")

        if analysis.ai_analysis:
            lines.append("\n## 🤖 Analisis AI\n")
            lines.append(analysis.ai_analysis)

        if analysis.recommendations:
            lines.append("\n## 💡 Rekomendasi Mitigasi\n")
            for i, rec in enumerate(analysis.recommendations, 1):
                lines.append(f"{i}. {rec}")

        if analysis.next_commands:
            lines.append("\n## 🔧 Perintah Lanjutan yang Disarankan\n")
            for cmd in analysis.next_commands:
                lines.append(f"```bash\n{cmd}\n```\n")

    if include_raw and scan.raw_output:
        lines.append("\n## 📄 Output Mentah Nmap\n")
        lines.append("```")
        lines.append(scan.raw_output)
        lines.append("```")

    lines.append(f"\n---\n*Laporan dibuat oleh NmapSLM pada {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")

    return "\n".join(lines)


def _generate_json(
    scan: NmapScanResult,
    analysis: Optional[ScanAnalysis]
) -> str:
    data = {
        "meta": {
            "generated_at": datetime.now().isoformat(),
            "generator": "NmapSLM v1.0.0",
        },
        "scan": scan.model_dump(mode="json"),
        "analysis": analysis.model_dump(mode="json") if analysis else None,
    }
    return json.dumps(data, indent=2, ensure_ascii=False, default=str)


def _generate_pdf(
    scan: NmapScanResult,
    analysis: Optional[ScanAnalysis],
    output_path: Path,
    include_raw: bool
) -> None:
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.lib import colors
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
            HRFlowable, KeepTogether
        )
        from reportlab.lib.enums import TA_LEFT, TA_CENTER

    except ImportError:
        # Fallback: save markdown as .txt inside pdf-named file
        md_content = _generate_markdown(scan, analysis, include_raw)
        output_path.write_text(md_content, encoding="utf-8")
        return

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle('NmapTitle', fontSize=20, fontName='Helvetica-Bold',
                               spaceAfter=12, textColor=colors.HexColor('#0f172a')))
    styles.add(ParagraphStyle('NmapH2', fontSize=14, fontName='Helvetica-Bold',
                               spaceAfter=8, textColor=colors.HexColor('#1e40af')))
    styles.add(ParagraphStyle('NmapH3', fontSize=12, fontName='Helvetica-Bold',
                               spaceAfter=6, textColor=colors.HexColor('#374151')))
    styles.add(ParagraphStyle('NmapBody', fontSize=9, fontName='Helvetica',
                               spaceAfter=4, leading=14))
    styles.add(ParagraphStyle('NmapCode', fontSize=8, fontName='Courier',
                               backColor=colors.HexColor('#f1f5f9'),
                               borderPadding=4, spaceAfter=4))
    styles.add(ParagraphStyle('NmapWarning', fontSize=9, fontName='Helvetica',
                               textColor=colors.HexColor('#92400e'),
                               backColor=colors.HexColor('#fef3c7'),
                               borderPadding=6, spaceAfter=6))

    story = []

    # Header
    story.append(Paragraph("Laporan Scan Nmap", styles['NmapTitle']))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#2563eb')))
    story.append(Spacer(1, 0.3*cm))

    # Scan info table
    info_data = [
        ["Scan ID", scan.scan_id],
        ["Command", scan.command],
        ["Waktu Mulai", scan.start_time.strftime('%Y-%m-%d %H:%M:%S')],
        ["Status", scan.status.value.upper()],
    ]
    if scan.end_time:
        elapsed = (scan.end_time - scan.start_time).total_seconds()
        info_data.append(["Durasi", f"{elapsed:.1f} detik"])

    info_table = Table(info_data, colWidths=[3*cm, 14*cm])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('FONTNAME', (1,0), (1,-1), 'Courier'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#f8fafc')),
        ('ROWBACKGROUNDS', (0,0), (-1,-1), [colors.white, colors.HexColor('#f8fafc')]),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 0.5*cm))

    # Executive Summary
    if analysis:
        story.append(Paragraph("Ringkasan Eksekutif", styles['NmapH2']))

        risk_colors = {
            "critical": "#dc2626", "high": "#ea580c",
            "medium": "#d97706", "low": "#16a34a", "info": "#2563eb"
        }
        risk_color = risk_colors.get(analysis.risk_assessment.value, "#6b7280")

        summary_data = [
            ["Ringkasan", analysis.summary],
            ["Total Host", str(analysis.total_hosts)],
            ["Port Terbuka", str(analysis.open_ports_count)],
            ["Level Risiko", analysis.risk_assessment.value.upper()],
        ]
        summary_table = Table(summary_data, colWidths=[3*cm, 14*cm])
        summary_table.setStyle(TableStyle([
            ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,-1), 9),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
            ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor(risk_color + '20')),
            ('TEXTCOLOR', (1,-1), (1,-1), colors.HexColor(risk_color)),
            ('FONTNAME', (1,-1), (1,-1), 'Helvetica-Bold'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('LEFTPADDING', (0,0), (-1,-1), 6),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 0.5*cm))

        # Legal notice
        if analysis.legal_notice:
            story.append(Paragraph(f"⚖️ {analysis.legal_notice}", styles['NmapWarning']))
            story.append(Spacer(1, 0.3*cm))

    # Hosts
    story.append(Paragraph("Hasil Scan Per Host", styles['NmapH2']))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e2e8f0')))
    story.append(Spacer(1, 0.2*cm))

    for host in scan.hosts:
        story.append(Paragraph(f"Host: {host.address} ({host.hostname or 'no hostname'})", styles['NmapH3']))
        open_ports = [p for p in host.ports if p.state == "open"]

        if open_ports:
            port_data = [["Port", "Protokol", "Layanan", "Versi"]]
            for port in open_ports:
                svc = port.service
                version = f"{svc.product} {svc.version}".strip() or "-"
                port_data.append([
                    str(port.port), port.protocol,
                    svc.name or "-",
                    version[:40] if version else "-"
                ])

            port_table = Table(port_data, colWidths=[1.5*cm, 2*cm, 3.5*cm, 10*cm])
            port_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1e40af')),
                ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('FONTSIZE', (0,0), (-1,-1), 8),
                ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f0f9ff')]),
                ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#bfdbfe')),
                ('LEFTPADDING', (0,0), (-1,-1), 4),
                ('TOPPADDING', (0,0), (-1,-1), 3),
                ('BOTTOMPADDING', (0,0), (-1,-1), 3),
            ]))
            story.append(port_table)
        else:
            story.append(Paragraph("Tidak ada port terbuka.", styles['NmapBody']))
        story.append(Spacer(1, 0.3*cm))

    # Risks & recommendations
    if analysis:
        if analysis.port_risks:
            story.append(Paragraph("Penilaian Risiko Port", styles['NmapH2']))
            risk_data = [["Port", "Layanan", "Risiko", "Deskripsi"]]
            risk_row_colors = {
                "critical": "#fef2f2", "high": "#fff7ed",
                "medium": "#fefce8", "low": "#f0fdf4", "info": "#eff6ff"
            }
            for risk in sorted(analysis.port_risks, key=lambda x: ["critical","high","medium","low","info"].index(x.risk_level.value)):
                risk_data.append([
                    str(risk.port), risk.service,
                    risk.risk_level.upper(), risk.description
                ])

            risk_table = Table(risk_data, colWidths=[1.5*cm, 3*cm, 2.5*cm, 10*cm])
            risk_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#7c3aed')),
                ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('FONTSIZE', (0,0), (-1,-1), 8),
                ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
                ('LEFTPADDING', (0,0), (-1,-1), 4),
                ('TOPPADDING', (0,0), (-1,-1), 3),
                ('BOTTOMPADDING', (0,0), (-1,-1), 3),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ]))
            story.append(risk_table)
            story.append(Spacer(1, 0.5*cm))

        if analysis.recommendations:
            story.append(Paragraph("💡 Rekomendasi Mitigasi", styles['NmapH2']))
            for i, rec in enumerate(analysis.recommendations, 1):
                story.append(Paragraph(f"{i}. {rec}", styles['NmapBody']))
            story.append(Spacer(1, 0.3*cm))

        if analysis.next_commands:
            story.append(Paragraph("🔧 Perintah Lanjutan", styles['NmapH2']))
            for cmd in analysis.next_commands:
                story.append(Paragraph(cmd, styles['NmapCode']))

    if include_raw and scan.raw_output:
        story.append(Spacer(1, 0.5*cm))
        story.append(Paragraph("Output Mentah Nmap", styles['NmapH2']))
        for line in scan.raw_output.split("\n")[:100]:  # Limit lines
            if line.strip():
                story.append(Paragraph(line, styles['NmapCode']))

    # Footer
    story.append(Spacer(1, 1*cm))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e2e8f0')))
    story.append(Paragraph(
        f"Laporan dibuat oleh NmapSLM v1.0.0 pada {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        styles['NmapBody']
    ))

    doc.build(story)
