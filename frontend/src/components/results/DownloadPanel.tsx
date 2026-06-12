"use client";

import { useState } from "react";
import { useScanStore } from "@/store/scanStore";
import { nmapApi } from "@/lib/api";
import { downloadBlob, cn } from "@/lib/utils";
import type { ExportFormat } from "@/types";
import {
  Download, FileText, FileCode, FileJson,
  CheckCircle2, AlertCircle, Loader2,
} from "lucide-react";
import { toast } from "sonner";

interface FormatOption {
  format: ExportFormat;
  label: string;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
  color: string;
  bg: string;
  border: string;
}

const FORMAT_OPTIONS: FormatOption[] = [
  {
    format: "pdf",
    label: "PDF Report",
    description: "Laporan lengkap berformat PDF. Siap cetak dan profesional.",
    icon: FileText,
    color: "text-red-400",
    bg: "bg-red-950/40",
    border: "border-red-800/60",
  },
  {
    format: "md",
    label: "Markdown",
    description: "Format Markdown ringan. Cocok untuk GitHub, Notion, dan wiki.",
    icon: FileCode,
    color: "text-blue-400",
    bg: "bg-blue-950/40",
    border: "border-blue-800/60",
  },
  {
    format: "json",
    label: "JSON Data",
    description: "Data mentah terstruktur. Ideal untuk integrasi dan pipeline.",
    icon: FileJson,
    color: "text-green-400",
    bg: "bg-green-950/40",
    border: "border-green-800/60",
  },
];

type DownloadState = "idle" | "loading" | "success" | "error";

export function DownloadPanel() {
  const { currentScan, currentScanId } = useScanStore();
  const [states, setStates] = useState<Record<ExportFormat, DownloadState>>({
    pdf: "idle", md: "idle", json: "idle",
  });
  const [includeRaw, setIncludeRaw] = useState(true);

  const scanId = currentScanId || currentScan?.scan_id;
  const canDownload = !!scanId && currentScan?.status === "completed";

  const handleDownload = async (format: ExportFormat) => {
    if (!scanId || states[format] === "loading") return;

    setStates((s) => ({ ...s, [format]: "loading" }));
    try {
      const { blob, filename } = await nmapApi.downloadReport(scanId, format, includeRaw);
      downloadBlob(blob, filename);
      setStates((s) => ({ ...s, [format]: "success" }));
      toast.success(`${filename} berhasil diunduh`);
      setTimeout(() => setStates((s) => ({ ...s, [format]: "idle" })), 3000);
    } catch (err: any) {
      setStates((s) => ({ ...s, [format]: "error" }));
      toast.error(`Gagal mengunduh: ${err.message}`);
      setTimeout(() => setStates((s) => ({ ...s, [format]: "idle" })), 3000);
    }
  };

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-5">

      {/* Header info */}
      <div className="flex items-center gap-2">
        <Download className="w-4 h-4 text-cyan-500" />
        <h3 className="text-sm font-semibold text-slate-200">Export Laporan</h3>
      </div>

      {!canDownload && (
        <div className="bg-amber-950/40 border border-amber-700/40 rounded-xl p-3 text-xs text-amber-300 flex gap-2">
          <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
          Scan harus selesai sebelum laporan dapat diunduh.
        </div>
      )}

      {/* Include raw toggle */}
      <label className="flex items-center gap-3 cursor-pointer">
        <div
          onClick={() => setIncludeRaw(!includeRaw)}
          className={cn(
            "relative w-10 h-5 rounded-full transition-colors cursor-pointer",
            includeRaw ? "bg-cyan-600" : "bg-slate-700"
          )}
        >
          <div className={cn(
            "absolute top-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform",
            includeRaw ? "translate-x-5" : "translate-x-0.5"
          )} />
        </div>
        <span className="text-sm text-slate-300">Sertakan output mentah Nmap</span>
      </label>

      {/* Format cards */}
      <div className="space-y-3">
        {FORMAT_OPTIONS.map((opt) => (
          <FormatCard
            key={opt.format}
            option={opt}
            state={states[opt.format]}
            disabled={!canDownload}
            onDownload={() => handleDownload(opt.format)}
          />
        ))}
      </div>

      {/* Scan summary */}
      {currentScan && (
        <div className="border border-slate-700/40 rounded-xl p-4 text-xs space-y-1.5">
          <div className="text-slate-500 font-medium mb-2">Info Scan</div>
          <InfoRow label="Scan ID" value={currentScan.scan_id.slice(0, 16) + "…"} mono />
          <InfoRow label="Command" value={currentScan.command} mono />
          <InfoRow label="Host" value={`${currentScan.hosts.length} ditemukan`} />
          <InfoRow label="Status" value={currentScan.status} />
        </div>
      )}
    </div>
  );
}

// ─── sub-components ───────────────────────────────────────────────────────

function FormatCard({
  option, state, disabled, onDownload,
}: {
  option: FormatOption;
  state: DownloadState;
  disabled: boolean;
  onDownload: () => void;
}) {
  const Icon = option.icon;
  const isLoading = state === "loading";
  const isSuccess = state === "success";
  const isError   = state === "error";

  return (
    <div className={cn(
      "rounded-xl border transition-all",
      disabled ? "opacity-40 border-slate-800" : `${option.border} ${option.bg}`,
    )}>
      <div className="flex items-start gap-4 p-4">
        <div className={cn(
          "w-10 h-10 rounded-xl flex items-center justify-center shrink-0",
          "bg-slate-900/60"
        )}>
          <Icon className={cn("w-5 h-5", option.color)} />
        </div>
        <div className="flex-1 min-w-0">
          <h4 className="text-sm font-semibold text-slate-200">{option.label}</h4>
          <p className="text-xs text-slate-500 mt-0.5 leading-relaxed">{option.description}</p>
        </div>
        <button
          onClick={onDownload}
          disabled={disabled || isLoading}
          className={cn(
            "shrink-0 flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-semibold transition-all",
            disabled
              ? "bg-slate-800 text-slate-600 cursor-not-allowed"
              : isSuccess
              ? "bg-green-600/20 text-green-400 border border-green-700"
              : isError
              ? "bg-red-600/20 text-red-400 border border-red-700"
              : `bg-slate-800 hover:bg-slate-700 ${option.color} border ${option.border}`,
            isLoading && "opacity-70 cursor-wait"
          )}
        >
          {isLoading && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
          {isSuccess && <CheckCircle2 className="w-3.5 h-3.5" />}
          {isError   && <AlertCircle  className="w-3.5 h-3.5" />}
          {!isLoading && !isSuccess && !isError && <Download className="w-3.5 h-3.5" />}
          <span>
            {isLoading ? "Proses…"
              : isSuccess ? "Berhasil"
              : isError   ? "Gagal"
              : "Unduh"}
          </span>
        </button>
      </div>
    </div>
  );
}

function InfoRow({ label, value, mono = false }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex gap-2">
      <span className="text-slate-600 w-16 shrink-0">{label}</span>
      <span className={cn(
        "text-slate-400 truncate",
        mono && "font-mono"
      )}>{value}</span>
    </div>
  );
}
