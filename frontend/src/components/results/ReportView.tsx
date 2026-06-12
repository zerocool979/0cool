"use client";

import { useMemo } from "react";
import { useScanStore } from "@/store/scanStore";
import { cn, formatDuration, formatDate } from "@/lib/utils";
import { RISK_CONFIG } from "@/types";
import { FileText, Loader2 } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export function ReportView() {
  const { currentScan, currentAnalysis, isAnalyzing } = useScanStore();

  const markdown = useMemo(() => {
    if (!currentScan) return "";
    return buildMarkdown(currentScan, currentAnalysis);
  }, [currentScan, currentAnalysis]);

  if (isAnalyzing) {
    return (
      <div className="flex flex-col h-full items-center justify-center gap-4">
        <Loader2 className="w-8 h-8 text-violet-400 animate-spin" />
        <p className="text-sm text-slate-400">Menyusun laporan…</p>
      </div>
    );
  }

  if (!currentScan) {
    return (
      <div className="flex flex-col h-full items-center justify-center gap-3">
        <FileText className="w-10 h-10 text-slate-700" />
        <p className="text-sm text-slate-500">Laporan belum tersedia</p>
      </div>
    );
  }

  const risk = currentAnalysis?.risk_assessment;
  const riskCfg = risk ? RISK_CONFIG[risk] : null;

  return (
    <div className="flex-1 overflow-y-auto">
      {/* Report header card */}
      <div className={cn(
        "mx-4 mt-4 p-5 rounded-xl border",
        riskCfg ? `${riskCfg.bg} ${riskCfg.border}` : "bg-slate-800/40 border-slate-700/40"
      )}>
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="text-base font-bold text-slate-100 mb-1">Laporan Scan Nmap</h2>
            <p className="text-xs text-slate-400 font-mono">{currentScan.command}</p>
          </div>
          {riskCfg && (
            <span className={cn(
              "text-xs font-bold px-3 py-1 rounded-full border shrink-0",
              riskCfg.bg, riskCfg.color, riskCfg.border
            )}>
              {riskCfg.icon} {riskCfg.label}
            </span>
          )}
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-4">
          <MetaItem label="Scan ID" value={currentScan.scan_id.slice(0, 8)} mono />
          <MetaItem label="Waktu" value={formatDate(currentScan.start_time)} />
          <MetaItem label="Durasi" value={formatDuration(currentScan.run_stats.elapsed)} />
          <MetaItem label="Host" value={`${currentScan.hosts.length} ditemukan`} />
        </div>
      </div>

      {/* Markdown body */}
      <div className="px-4 pb-8 pt-4">
        <div className="prose prose-invert prose-sm max-w-none
          prose-headings:text-slate-200 prose-headings:font-semibold
          prose-p:text-slate-300 prose-p:leading-relaxed
          prose-code:text-cyan-300 prose-code:bg-slate-800 prose-code:px-1 prose-code:rounded
          prose-pre:bg-slate-950 prose-pre:border prose-pre:border-slate-800
          prose-table:text-xs prose-th:text-slate-400 prose-td:text-slate-300
          prose-strong:text-slate-100 prose-a:text-cyan-400
          prose-hr:border-slate-700 prose-li:text-slate-300">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {markdown}
          </ReactMarkdown>
        </div>
      </div>
    </div>
  );
}

function MetaItem({ label, value, mono = false }: { label: string; value: string; mono?: boolean }) {
  return (
    <div>
      <div className="text-[10px] uppercase tracking-wide text-slate-500">{label}</div>
      <div className={cn("text-xs text-slate-200 mt-0.5 truncate", mono && "font-mono")}>{value}</div>
    </div>
  );
}

// ─── report builder ───────────────────────────────────────────────────────

function buildMarkdown(scan: any, analysis: any): string {
  const lines: string[] = [];

  lines.push("## Ringkasan Eksekutif");
  if (analysis?.summary) {
    lines.push(`\n${analysis.summary}\n`);
  }

  if (analysis) {
    lines.push(`| Metrik | Nilai |`);
    lines.push(`|--------|-------|`);
    lines.push(`| Total Host | ${analysis.total_hosts} |`);
    lines.push(`| Port Terbuka | ${analysis.open_ports_count} |`);
    lines.push(`| Level Risiko | **${analysis.risk_assessment?.toUpperCase()}** |`);
    lines.push(`| Kerentanan | ${analysis.vulnerabilities?.length ?? 0} |`);
    lines.push("");
  }

  if (analysis?.legal_notice) {
    lines.push("---");
    lines.push("### ⚖️ Catatan Hukum");
    lines.push(`\n> ${analysis.legal_notice}\n`);
  }

  lines.push("---");
  lines.push("## Hasil Scan Per Host");

  for (const host of scan.hosts ?? []) {
    lines.push(`\n### 🖥️ \`${host.address}\`${host.hostname ? ` (${host.hostname})` : ""}`);
    lines.push(`**Status:** ${host.status}`);
    if (host.os_matches?.[0]) {
      lines.push(`**OS:** ${host.os_matches[0].name} (${host.os_matches[0].accuracy}%)`);
    }

    const open = (host.ports ?? []).filter((p: any) => p.state === "open");
    if (open.length > 0) {
      lines.push(`\n**Port Terbuka (${open.length})**\n`);
      lines.push("| Port | Protokol | Layanan | Versi |");
      lines.push("|------|----------|---------|-------|");
      for (const p of open) {
        const ver = [p.service?.product, p.service?.version].filter(Boolean).join(" ");
        lines.push(`| ${p.port} | ${p.protocol} | ${p.service?.name || "-"} | ${ver || "-"} |`);
      }
    } else {
      lines.push("\n_Tidak ada port terbuka._");
    }
  }

  if (analysis?.port_risks?.length > 0) {
    lines.push("\n---");
    lines.push("## 🚨 Penilaian Risiko Port\n");
    lines.push("| Port | Layanan | Risiko | Keterangan |");
    lines.push("|------|---------|--------|------------|");
    for (const r of analysis.port_risks) {
      lines.push(`| ${r.port} | ${r.service} | **${r.risk_level.toUpperCase()}** | ${r.description} |`);
    }
  }

  if (analysis?.vulnerabilities?.length > 0) {
    lines.push("\n---");
    lines.push("## 🔍 Kerentanan Teridentifikasi\n");
    for (const v of analysis.vulnerabilities) lines.push(`- ${v}`);
  }

  if (analysis?.ai_analysis) {
    lines.push("\n---");
    lines.push("## 🤖 Analisis AI\n");
    lines.push(analysis.ai_analysis);
  }

  if (analysis?.recommendations?.length > 0) {
    lines.push("\n---");
    lines.push("## 💡 Rekomendasi Mitigasi\n");
    analysis.recommendations.forEach((r: string, i: number) => lines.push(`${i + 1}. ${r}`));
  }

  if (analysis?.next_commands?.length > 0) {
    lines.push("\n---");
    lines.push("## 🔧 Perintah Lanjutan\n");
    for (const cmd of analysis.next_commands) {
      lines.push("```bash");
      lines.push(cmd);
      lines.push("```\n");
    }
  }

  lines.push("\n---");
  lines.push(`*Laporan dibuat oleh **NmapSLM** pada ${new Date().toLocaleString("id-ID")}*`);

  return lines.join("\n");
}
