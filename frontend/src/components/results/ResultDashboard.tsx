"use client";

import { useScanStore } from "@/store/scanStore";
import { RawOutput } from "./RawOutput";
import { AnalysisView } from "./AnalysisView";
import { RecommendationView } from "./RecommendationView";
import { ReportView } from "./ReportView";
import { DownloadPanel } from "./DownloadPanel";
import { cn } from "@/lib/utils";
import {
  Terminal,
  Brain,
  Lightbulb,
  FileText,
  Download,
  Loader2,
  ScanSearch,
} from "lucide-react";
import { RISK_CONFIG } from "@/types";

const TABS = [
  { id: "raw",             label: "Raw",           icon: Terminal,   shortLabel: "Raw"   },
  { id: "analysis",        label: "Analisis",      icon: Brain,      shortLabel: "Analisis" },
  { id: "recommendations", label: "Saran",         icon: Lightbulb,  shortLabel: "Saran" },
  { id: "report",          label: "Laporan",       icon: FileText,   shortLabel: "Laporan" },
  { id: "download",        label: "Download",      icon: Download,   shortLabel: "DL"    },
] as const;

export function ResultDashboard() {
  const {
    currentScan,
    currentAnalysis,
    scanStatus,
    isAnalyzing,
    activeTab,
    setActiveTab,
  } = useScanStore();

  const hasResult  = !!currentScan;
  const hasAnalysis = !!currentAnalysis;
  const isRunning  = scanStatus === "running";

  // ── empty state ──────────────────────────────────────────────────────────
  if (!hasResult && !isRunning) {
    return (
      <div className="flex flex-col h-full items-center justify-center gap-5 text-center px-8">
        <div className="w-16 h-16 rounded-2xl bg-slate-800 border border-slate-700 flex items-center justify-center">
          <ScanSearch className="w-8 h-8 text-slate-600" />
        </div>
        <div>
          <h3 className="text-sm font-semibold text-slate-400 mb-1">Belum Ada Hasil</h3>
          <p className="text-xs text-slate-600 leading-relaxed max-w-xs">
            Masukkan perintah nmap di panel kiri dan tekan Scan. Hasil akan ditampilkan di sini.
          </p>
        </div>
        <div className="grid grid-cols-5 gap-2 w-full max-w-sm opacity-30">
          {TABS.map((t) => (
            <div key={t.id} className="h-8 bg-slate-800 rounded-lg" />
          ))}
        </div>
      </div>
    );
  }

  // ── scanning progress ─────────────────────────────────────────────────────
  if (isRunning && !hasResult) {
    return (
      <div className="flex flex-col h-full items-center justify-center gap-4">
        <div className="relative">
          <div className="w-16 h-16 rounded-full border-2 border-cyan-800 border-t-cyan-400 animate-spin" />
          <ScanSearch className="w-6 h-6 text-cyan-400 absolute inset-0 m-auto" />
        </div>
        <div className="text-center">
          <p className="text-sm font-semibold text-slate-300">Scanning jaringan…</p>
          <p className="text-xs text-slate-500 mt-1">Pantau progress di panel kiri</p>
        </div>
      </div>
    );
  }

  // ── risk badge for tab bar ────────────────────────────────────────────────
  const risk = currentAnalysis?.risk_assessment;
  const riskCfg = risk ? RISK_CONFIG[risk] : null;

  return (
    <div className="flex flex-col h-full bg-slate-900">
      {/* ── Tab bar ────────────────────────────────────────────────────────── */}
      <div className="flex items-center border-b border-slate-800 px-3 gap-0.5 shrink-0">
        {TABS.map((tab) => {
          const Icon = tab.icon;
          const active = activeTab === tab.id;
          const needsAnalysis = tab.id !== "raw" && tab.id !== "download";
          const disabled = needsAnalysis && !hasAnalysis && !isAnalyzing;

          return (
            <button
              key={tab.id}
              onClick={() => !disabled && setActiveTab(tab.id as typeof activeTab)}
              disabled={disabled}
              className={cn(
                "flex items-center gap-1.5 px-3 py-2.5 text-xs font-medium rounded-t-lg transition-colors relative",
                active
                  ? "text-cyan-300 border-b-2 border-cyan-400 -mb-px"
                  : "text-slate-500 hover:text-slate-300 border-b-2 border-transparent",
                disabled && "opacity-30 cursor-not-allowed hover:text-slate-500"
              )}
            >
              {tab.id === "analysis" && isAnalyzing ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Icon className="w-3.5 h-3.5" />
              )}
              <span className="hidden sm:inline">{tab.label}</span>
              <span className="sm:hidden">{tab.shortLabel}</span>

              {/* risk badge on analysis tab */}
              {tab.id === "analysis" && riskCfg && (
                <span className={cn(
                  "text-[10px] px-1.5 py-0.5 rounded-full font-semibold ml-0.5",
                  riskCfg.bg, riskCfg.color, `border ${riskCfg.border}`
                )}>
                  {riskCfg.label}
                </span>
              )}
            </button>
          );
        })}

        {/* scan meta */}
        {currentScan && (
          <div className="ml-auto text-xs text-slate-600 pr-1 hidden md:block truncate max-w-[200px]">
            {currentScan.command}
          </div>
        )}
      </div>

      {/* ── Tab content ───────────────────────────────────────────────────── */}
      <div className="flex-1 overflow-hidden">
        {activeTab === "raw"             && <RawOutput />}
        {activeTab === "analysis"        && <AnalysisView />}
        {activeTab === "recommendations" && <RecommendationView />}
        {activeTab === "report"          && <ReportView />}
        {activeTab === "download"        && <DownloadPanel />}
      </div>
    </div>
  );
}
