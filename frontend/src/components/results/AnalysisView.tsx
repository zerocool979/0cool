"use client";

import { useScanStore } from "@/store/scanStore";
import { cn } from "@/lib/utils";
import { RISK_CONFIG, type RiskLevel, type PortRisk } from "@/types";
import {
  ShieldAlert, ShieldCheck, ShieldQuestion,
  Loader2, AlertTriangle, Scale,
  ChevronUp, ChevronDown,
} from "lucide-react";
import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export function AnalysisView() {
  const { currentAnalysis, isAnalyzing } = useScanStore();

  if (isAnalyzing) {
    return (
      <div className="flex flex-col h-full items-center justify-center gap-4">
        <div className="relative">
          <div className="w-16 h-16 rounded-full border-2 border-violet-800 border-t-violet-400 animate-spin" />
          <Loader2 className="w-6 h-6 text-violet-400 absolute inset-0 m-auto animate-spin" />
        </div>
        <div className="text-center">
          <p className="text-sm font-semibold text-slate-300">Menganalisis dengan AI…</p>
          <p className="text-xs text-slate-500 mt-1">QwenNmap sedang memproses hasil scan</p>
        </div>
      </div>
    );
  }

  if (!currentAnalysis) {
    return (
      <div className="flex flex-col h-full items-center justify-center gap-3 text-center px-8">
        <ShieldQuestion className="w-10 h-10 text-slate-700" />
        <p className="text-sm text-slate-500">Analisis belum tersedia</p>
        <p className="text-xs text-slate-600">Scan harus selesai terlebih dahulu</p>
      </div>
    );
  }

  const riskCfg = RISK_CONFIG[currentAnalysis.risk_assessment];

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-5">

      {/* ── Risk overview ───────────────────────────────────────────────── */}
      <section className={cn(
        "rounded-xl border p-4",
        riskCfg.bg, riskCfg.border
      )}>
        <div className="flex items-start gap-3">
          <RiskIcon level={currentAnalysis.risk_assessment} />
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <span className={cn("text-xs font-bold tracking-wider uppercase", riskCfg.color)}>
                {riskCfg.icon} Risiko {riskCfg.label}
              </span>
            </div>
            <p className="text-sm text-slate-200 leading-relaxed">{currentAnalysis.summary}</p>
          </div>
        </div>

        {/* quick stats */}
        <div className="grid grid-cols-3 gap-3 mt-4">
          <Stat label="Host Aktif"   value={currentAnalysis.total_hosts}      />
          <Stat label="Port Terbuka" value={currentAnalysis.open_ports_count} />
          <Stat label="Kerentanan"   value={currentAnalysis.vulnerabilities.length} />
        </div>
      </section>

      {/* ── Legal notice ────────────────────────────────────────────────── */}
      {currentAnalysis.legal_notice && (
        <LegalCard text={currentAnalysis.legal_notice} />
      )}

      {/* ── AI Analysis text ────────────────────────────────────────────── */}
      {currentAnalysis.ai_analysis && (
        <section>
          <SectionTitle icon={ShieldAlert} label="Analisis AI" />
          <div className="prose prose-invert prose-sm max-w-none bg-slate-800/50 border border-slate-700/50 rounded-xl p-4">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {currentAnalysis.ai_analysis}
            </ReactMarkdown>
          </div>
        </section>
      )}

      {/* ── Port risk table ──────────────────────────────────────────────── */}
      {currentAnalysis.port_risks.length > 0 && (
        <section>
          <SectionTitle icon={ShieldAlert} label="Risiko Per Port" />
          <PortRiskTable risks={currentAnalysis.port_risks} />
        </section>
      )}

      {/* ── Vulnerabilities ─────────────────────────────────────────────── */}
      {currentAnalysis.vulnerabilities.length > 0 && (
        <section>
          <SectionTitle icon={AlertTriangle} label="Kerentanan Teridentifikasi" />
          <ul className="space-y-2">
            {currentAnalysis.vulnerabilities.map((v, i) => (
              <li
                key={i}
                className="flex gap-2 text-sm text-slate-300 bg-slate-800/40 border border-slate-700/40 rounded-lg px-3 py-2"
              >
                <span className="text-red-400 mt-0.5">•</span>
                {v}
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}

// ─── helpers ──────────────────────────────────────────────────────────────

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="text-center">
      <div className="text-xl font-bold text-slate-100">{value}</div>
      <div className="text-xs text-slate-500">{label}</div>
    </div>
  );
}

function RiskIcon({ level }: { level: RiskLevel }) {
  const isSafe = level === "low" || level === "info";
  const Icon   = isSafe ? ShieldCheck : ShieldAlert;
  const colors: Record<RiskLevel, string> = {
    critical: "text-red-400", high: "text-orange-400",
    medium: "text-yellow-400", low: "text-green-400", info: "text-blue-400",
  };
  return <Icon className={cn("w-7 h-7 shrink-0 mt-0.5", colors[level])} />;
}

function LegalCard({ text }: { text: string }) {
  const [expanded, setExpanded] = useState(false);
  const short = text.slice(0, 120);
  return (
    <section className="bg-amber-950/40 border border-amber-700/40 rounded-xl p-4">
      <div className="flex items-center gap-2 mb-2">
        <Scale className="w-4 h-4 text-amber-400 shrink-0" />
        <span className="text-xs font-semibold text-amber-400 uppercase tracking-wide">Catatan Hukum UU ITE</span>
      </div>
      <p className="text-xs text-amber-300/80 leading-relaxed">
        {expanded ? text : short + (text.length > 120 ? "…" : "")}
      </p>
      {text.length > 120 && (
        <button
          onClick={() => setExpanded(!expanded)}
          className="mt-1.5 text-xs text-amber-500 hover:text-amber-300 flex items-center gap-1"
        >
          {expanded ? <><ChevronUp className="w-3 h-3" />Sembunyikan</> : <><ChevronDown className="w-3 h-3" />Lihat selengkapnya</>}
        </button>
      )}
    </section>
  );
}

function SectionTitle({ icon: Icon, label }: { icon: React.ComponentType<{ className?: string }>; label: string }) {
  return (
    <div className="flex items-center gap-2 mb-3">
      <Icon className="w-4 h-4 text-cyan-500" />
      <h3 className="text-sm font-semibold text-slate-200">{label}</h3>
    </div>
  );
}

const RISK_ORDER: RiskLevel[] = ["critical", "high", "medium", "low", "info"];

function PortRiskTable({ risks }: { risks: PortRisk[] }) {
  const sorted = [...risks].sort(
    (a, b) => RISK_ORDER.indexOf(a.risk_level) - RISK_ORDER.indexOf(b.risk_level)
  );

  return (
    <div className="border border-slate-700/60 rounded-xl overflow-hidden">
      <table className="w-full text-xs">
        <thead>
          <tr className="bg-slate-800/60 text-slate-500 border-b border-slate-700/40">
            <th className="text-left px-4 py-2.5 font-medium">PORT</th>
            <th className="text-left px-4 py-2.5 font-medium">LAYANAN</th>
            <th className="text-left px-4 py-2.5 font-medium">RISIKO</th>
            <th className="text-left px-4 py-2.5 font-medium hidden sm:table-cell">DESKRIPSI</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((r) => {
            const cfg = RISK_CONFIG[r.risk_level];
            return (
              <tr
                key={`${r.port}-${r.protocol}`}
                className="border-b border-slate-800/60 hover:bg-slate-800/30 transition-colors"
              >
                <td className="px-4 py-2.5 font-mono font-bold text-cyan-300">{r.port}</td>
                <td className="px-4 py-2.5 text-slate-300">{r.service}</td>
                <td className="px-4 py-2.5">
                  <span className={cn(
                    "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold border",
                    cfg.bg, cfg.color, cfg.border
                  )}>
                    {cfg.icon} {cfg.label}
                  </span>
                </td>
                <td className="px-4 py-2.5 text-slate-500 hidden sm:table-cell">{r.description}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
