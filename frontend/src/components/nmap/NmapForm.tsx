"use client";

import { useState, useRef, useEffect } from "react";
import { Send, AlertTriangle, Terminal, ChevronDown, X, Loader2 } from "lucide-react";
import { useScanStore } from "@/store/scanStore";
import { useScanWebSocket } from "@/hooks/useWebSocket";
import { NMAP_EXAMPLES, cn } from "@/lib/utils";

export function NmapForm() {
  const [command, setCommand] = useState("nmap -sV ");
  const [showExamples, setShowExamples] = useState(false);
  const [showWarning, setShowWarning] = useState(true);
  const inputRef = useRef<HTMLInputElement>(null);

  const { scanStatus, progressLines } = useScanStore();
  const { isConnected, sendScan, cancelScan } = useScanWebSocket();

  const isRunning = scanStatus === "running";

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!command.trim() || isRunning) return;
    sendScan(command.trim());
  };

  const handleExample = (cmd: string) => {
    setCommand(cmd);
    setShowExamples(false);
    inputRef.current?.focus();
  };

  return (
    <div className="flex flex-col h-full bg-slate-900">
      {/* Header */}
      <div className="px-4 py-3 border-b border-slate-800 flex items-center gap-2">
        <Terminal className="w-4 h-4 text-cyan-400" />
        <span className="text-sm font-semibold text-slate-200">Nmap Scanner</span>
        <div className="ml-auto flex items-center gap-1.5">
          <div className={cn(
            "w-2 h-2 rounded-full",
            isConnected ? "bg-green-400 animate-pulse" : "bg-red-500"
          )} />
          <span className={cn(
            "text-xs",
            isConnected ? "text-green-400" : "text-red-400"
          )}>
            {isConnected ? "Terhubung" : "Terputus"}
          </span>
        </div>
      </div>

      {/* Legal Warning */}
      {showWarning && (
        <div className="mx-4 mt-3 p-3 bg-amber-950/60 border border-amber-700/60 rounded-lg text-xs text-amber-300 flex gap-2">
          <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0 text-amber-400" />
          <div className="flex-1">
            <span className="font-semibold block mb-0.5">Perhatian Hukum (UU ITE Pasal 30)</span>
            Scanning jaringan tanpa izin adalah tindak pidana. Pastikan Anda memiliki izin eksplisit dari pemilik jaringan.
          </div>
          <button onClick={() => setShowWarning(false)} className="text-amber-500 hover:text-amber-300">
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Command Input */}
      <form onSubmit={handleSubmit} className="px-4 pt-4 pb-2">
        <div className="relative">
          <div className="flex gap-2">
            <div className="flex-1 relative">
              <input
                ref={inputRef}
                type="text"
                value={command}
                onChange={(e) => setCommand(e.target.value)}
                placeholder="nmap -sV 192.168.1.1"
                disabled={isRunning}
                className={cn(
                  "w-full bg-slate-800 text-slate-100 font-mono text-sm",
                  "border rounded-lg px-4 py-2.5 pr-10",
                  "placeholder:text-slate-500 outline-none",
                  "focus:border-cyan-600 focus:ring-1 focus:ring-cyan-600/30",
                  "transition-colors disabled:opacity-50",
                  isRunning ? "border-slate-700" : "border-slate-700 hover:border-slate-600"
                )}
                spellCheck={false}
                autoComplete="off"
              />
              <button
                type="button"
                onClick={() => setShowExamples(!showExamples)}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
              >
                <ChevronDown className={cn("w-4 h-4 transition-transform", showExamples && "rotate-180")} />
              </button>
            </div>

            {isRunning ? (
              <button
                type="button"
                onClick={cancelScan}
                className="px-4 py-2.5 bg-red-600 hover:bg-red-500 text-white rounded-lg text-sm font-medium flex items-center gap-2 transition-colors"
              >
                <X className="w-4 h-4" />
                Stop
              </button>
            ) : (
              <button
                type="submit"
                disabled={!command.trim() || !isConnected}
                className={cn(
                  "px-4 py-2.5 rounded-lg text-sm font-medium flex items-center gap-2 transition-colors",
                  "bg-cyan-600 hover:bg-cyan-500 text-white",
                  "disabled:opacity-40 disabled:cursor-not-allowed"
                )}
              >
                <Send className="w-4 h-4" />
                Scan
              </button>
            )}
          </div>

          {/* Examples Dropdown */}
          {showExamples && (
            <div className="absolute top-full left-0 right-12 mt-1 z-10 bg-slate-800 border border-slate-700 rounded-lg shadow-xl overflow-hidden">
              <div className="px-3 py-1.5 text-xs text-slate-500 border-b border-slate-700">
                Contoh perintah
              </div>
              {NMAP_EXAMPLES.map((ex) => (
                <button
                  key={ex.command}
                  onClick={() => handleExample(ex.command)}
                  className="w-full text-left px-3 py-2 hover:bg-slate-700 transition-colors"
                >
                  <div className="text-xs text-slate-400">{ex.label}</div>
                  <div className="text-xs font-mono text-cyan-400">{ex.command}</div>
                </button>
              ))}
            </div>
          )}
        </div>
      </form>

      {/* Progress Output */}
      <div className="flex-1 mx-4 mb-4 overflow-hidden">
        <div className="h-full bg-slate-950/80 border border-slate-800 rounded-lg overflow-hidden flex flex-col">
          <div className="px-3 py-1.5 border-b border-slate-800 flex items-center gap-2">
            {isRunning && <Loader2 className="w-3 h-3 text-cyan-400 animate-spin" />}
            <span className="text-xs text-slate-500 font-mono">
              {isRunning ? "Scanning..." : progressLines.length > 0 ? `${progressLines.length} baris output` : "Menunggu scan..."}
            </span>
          </div>
          <ScanProgressOutput lines={progressLines} isRunning={isRunning} />
        </div>
      </div>
    </div>
  );
}

function ScanProgressOutput({
  lines,
  isRunning,
}: {
  lines: string[];
  isRunning: boolean;
}) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [lines]);

  if (lines.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center text-slate-600 text-xs font-mono">
        {isRunning ? "Memulai scan..." : "Output scan akan muncul di sini"}
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-3 font-mono text-xs space-y-0.5">
      {lines.map((line, i) => (
        <div
          key={i}
          className={cn(
            "leading-relaxed",
            line.includes("open") && "text-green-400",
            line.includes("filtered") && "text-yellow-500",
            line.includes("closed") && "text-slate-600",
            line.includes("WARNING") && "text-amber-400",
            line.includes("ERROR") && "text-red-400",
            !line.includes("open") && !line.includes("filtered") && !line.includes("closed")
              && !line.includes("WARNING") && !line.includes("ERROR") && "text-slate-400"
          )}
        >
          {line}
        </div>
      ))}
      {isRunning && (
        <div className="text-cyan-400 animate-pulse">█</div>
      )}
      <div ref={bottomRef} />
    </div>
  );
}
