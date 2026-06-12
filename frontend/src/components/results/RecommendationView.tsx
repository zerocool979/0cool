"use client";

import { useState } from "react";
import { useScanStore } from "@/store/scanStore";
import { cn, copyToClipboard } from "@/lib/utils";
import { Lightbulb, Terminal, Copy, Check, ChevronRight, Loader2 } from "lucide-react";

export function RecommendationView() {
  const { currentAnalysis, isAnalyzing } = useScanStore();

  if (isAnalyzing) {
    return <LoadingState />;
  }

  if (!currentAnalysis) {
    return <EmptyState />;
  }

  const { recommendations, next_commands, port_risks } = currentAnalysis;

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-6">

      {/* ── Mitigasi per port ────────────────────────────────────────────── */}
      {port_risks.length > 0 && (
        <section>
          <SectionTitle icon={Lightbulb} label="Mitigasi Port Berisiko" />
          <div className="space-y-2">
            {port_risks
              .filter((r) => ["critical", "high", "medium"].includes(r.risk_level))
              .sort((a, b) => ["critical","high","medium","low","info"].indexOf(a.risk_level)
                           - ["critical","high","medium","low","info"].indexOf(b.risk_level))
              .map((risk) => (
                <PortMitigationCard
                  key={`${risk.port}-${risk.protocol}`}
                  port={risk.port}
                  service={risk.service}
                  riskLevel={risk.risk_level}
                  description={risk.description}
                  recommendation={risk.recommendation}
                />
              ))}
          </div>
        </section>
      )}

      {/* ── General recommendations ─────────────────────────────────────── */}
      {recommendations.length > 0 && (
        <section>
          <SectionTitle icon={Lightbulb} label="Rekomendasi Umum" />
          <div className="space-y-2">
            {recommendations.map((rec, i) => (
              <div
                key={i}
                className="flex gap-3 bg-slate-800/40 border border-slate-700/40 rounded-xl px-4 py-3"
              >
                <span className="text-cyan-500 font-bold text-sm mt-0.5 shrink-0">{i + 1}.</span>
                <p className="text-sm text-slate-300 leading-relaxed">{rec}</p>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* ── Next commands ───────────────────────────────────────────────── */}
      {next_commands.length > 0 && (
        <section>
          <SectionTitle icon={Terminal} label="Perintah Lanjutan yang Disarankan" />
          <p className="text-xs text-slate-500 mb-3">
            Klik untuk menyalin perintah ke clipboard
          </p>
          <div className="space-y-2">
            {next_commands.map((cmd, i) => (
              <CommandCard key={i} command={cmd} />
            ))}
          </div>
        </section>
      )}

      {recommendations.length === 0 && next_commands.length === 0 && port_risks.length === 0 && (
        <EmptyState />
      )}
    </div>
  );
}

// ─── sub-components ───────────────────────────────────────────────────────

function SectionTitle({ icon: Icon, label }: { icon: React.ComponentType<{ className?: string }>; label: string }) {
  return (
    <div className="flex items-center gap-2 mb-3">
      <Icon className="w-4 h-4 text-cyan-500" />
      <h3 className="text-sm font-semibold text-slate-200">{label}</h3>
    </div>
  );
}

const RISK_COLORS: Record<string, { badge: string; left: string }> = {
  critical: { badge: "bg-red-950/60 text-red-400 border-red-800", left: "border-l-red-500" },
  high:     { badge: "bg-orange-950/60 text-orange-400 border-orange-800", left: "border-l-orange-500" },
  medium:   { badge: "bg-yellow-950/60 text-yellow-400 border-yellow-800", left: "border-l-yellow-500" },
  low:      { badge: "bg-green-950/60 text-green-400 border-green-800", left: "border-l-green-600" },
  info:     { badge: "bg-blue-950/60 text-blue-400 border-blue-800", left: "border-l-blue-600" },
};

function PortMitigationCard({
  port, service, riskLevel, description, recommendation,
}: {
  port: number;
  service: string;
  riskLevel: string;
  description: string;
  recommendation: string;
}) {
  const [expanded, setExpanded] = useState(false);
  const colors = RISK_COLORS[riskLevel] ?? RISK_COLORS.info;

  return (
    <div className={cn(
      "bg-slate-800/40 border border-slate-700/40 rounded-xl border-l-4 overflow-hidden",
      colors.left
    )}>
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-slate-800/60 transition-colors"
      >
        <span className="font-mono font-bold text-cyan-300 text-sm w-12 shrink-0">{port}</span>
        <span className="text-sm text-slate-200 flex-1">{service}</span>
        <span className={cn(
          "text-[10px] font-bold uppercase px-2 py-0.5 rounded-full border shrink-0",
          colors.badge
        )}>
          {riskLevel}
        </span>
        <ChevronRight className={cn(
          "w-4 h-4 text-slate-500 transition-transform shrink-0",
          expanded && "rotate-90"
        )} />
      </button>

      {expanded && (
        <div className="px-4 pb-4 space-y-2 border-t border-slate-700/40 pt-3">
          <div>
            <span className="text-xs text-slate-500 uppercase tracking-wide">Risiko</span>
            <p className="text-xs text-slate-300 mt-0.5">{description}</p>
          </div>
          <div>
            <span className="text-xs text-slate-500 uppercase tracking-wide">Mitigasi</span>
            <p className="text-xs text-cyan-300 mt-0.5 leading-relaxed">{recommendation}</p>
          </div>
        </div>
      )}
    </div>
  );
}

function CommandCard({ command }: { command: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    copyToClipboard(command).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  return (
    <button
      onClick={handleCopy}
      className="w-full group flex items-center gap-3 bg-slate-950/60 border border-slate-700/60 hover:border-cyan-800 rounded-xl px-4 py-3 text-left transition-colors"
    >
      <Terminal className="w-4 h-4 text-slate-500 group-hover:text-cyan-500 shrink-0 transition-colors" />
      <code className="flex-1 text-xs font-mono text-slate-300 group-hover:text-cyan-300 transition-colors">
        {command}
      </code>
      <span className="shrink-0 text-slate-600 group-hover:text-slate-400 transition-colors">
        {copied
          ? <Check className="w-3.5 h-3.5 text-green-400" />
          : <Copy className="w-3.5 h-3.5" />}
      </span>
    </button>
  );
}

function LoadingState() {
  return (
    <div className="flex flex-col h-full items-center justify-center gap-4">
      <Loader2 className="w-8 h-8 text-violet-400 animate-spin" />
      <p className="text-sm text-slate-400">Memproses rekomendasi…</p>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-col h-full items-center justify-center gap-3 text-center px-8">
      <Lightbulb className="w-10 h-10 text-slate-700" />
      <p className="text-sm text-slate-500">Rekomendasi belum tersedia</p>
      <p className="text-xs text-slate-600">Tunggu analisis AI selesai</p>
    </div>
  );
}
