"use client";

import { useScanStore } from "@/store/scanStore";
import { cn, formatDate } from "@/lib/utils";
import { RISK_CONFIG, STATUS_CONFIG } from "@/types";
import { Shield, Cpu, Clock, Activity } from "lucide-react";

export function Header() {
  const { currentScan, currentAnalysis, scanStatus, ollamaStatus, ollamaModels } = useScanStore();

  const risk = currentAnalysis?.risk_assessment;
  const riskCfg = risk ? RISK_CONFIG[risk] : null;
  const statusCfg = scanStatus ? STATUS_CONFIG[scanStatus] : null;

  return (
    <header className="flex items-center gap-4 px-4 py-2.5 border-b border-slate-800 bg-slate-900 shrink-0">
      {/* App identity */}
      <div className="flex items-center gap-2 shrink-0">
        <Shield className="w-5 h-5 text-cyan-400" />
        <span className="text-sm font-bold text-slate-100 hidden md:block">
          NmapSLM
        </span>
        <span className="text-xs text-slate-600 hidden lg:block">
          Network Scanner + AI
        </span>
      </div>

      {/* Scan status pill */}
      {scanStatus && (
        <div className={cn(
          "flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full border",
          scanStatus === "running"   && "bg-blue-950/40 border-blue-800 text-blue-400",
          scanStatus === "completed" && "bg-green-950/40 border-green-800 text-green-400",
          scanStatus === "failed"    && "bg-red-950/40 border-red-800 text-red-400",
          scanStatus === "cancelled" && "bg-slate-800 border-slate-700 text-slate-400",
        )}>
          <Activity className={cn(
            "w-3 h-3",
            scanStatus === "running" && "animate-pulse"
          )} />
          <span>{statusCfg?.label}</span>
        </div>
      )}

      {/* Risk badge */}
      {riskCfg && (
        <span className={cn(
          "text-xs px-2.5 py-1 rounded-full border font-semibold hidden sm:inline-flex items-center gap-1",
          riskCfg.bg, riskCfg.border, riskCfg.color
        )}>
          {riskCfg.icon} {riskCfg.label}
        </span>
      )}

      {/* Scan command */}
      {currentScan && (
        <span className="text-xs font-mono text-slate-500 truncate hidden lg:block max-w-xs">
          {currentScan.command}
        </span>
      )}

      {/* Right: model + time */}
      <div className="ml-auto flex items-center gap-3">
        {/* Model info */}
        <div className="hidden sm:flex items-center gap-1.5 text-xs text-slate-600">
          <Cpu className="w-3.5 h-3.5" />
          <span className={cn(
            ollamaStatus === "ok" ? "text-slate-400" : "text-red-500"
          )}>
            {ollamaModels[0] || "Ollama"}
          </span>
        </div>

        {/* Time */}
        <LiveClock />
      </div>
    </header>
  );
}

function LiveClock() {
  const [time, setTime] = useState<string>("");

  useEffect(() => {
    const update = () => {
      const d = new Date();
      setTime(d.toLocaleTimeString("id-ID", { hour: "2-digit", minute: "2-digit", second: "2-digit" }));
    };
    update();
    const iv = setInterval(update, 1000);
    return () => clearInterval(iv);
  }, []);

  return (
    <div className="flex items-center gap-1 text-xs text-slate-600 hidden md:flex">
      <Clock className="w-3.5 h-3.5" />
      <span className="font-mono">{time}</span>
    </div>
  );
}

// Add missing react imports
import { useState, useEffect } from "react";
