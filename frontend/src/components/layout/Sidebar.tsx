"use client";

import { useEffect, useState } from "react";
import { useScanStore } from "@/store/scanStore";
import { nmapApi } from "@/lib/api";
import { cn, truncate, formatDate } from "@/lib/utils";
import { STATUS_CONFIG } from "@/types";
import {
  LayoutDashboard, History, Settings2,
  Shield, ChevronLeft, ChevronRight,
  Activity, Wifi, WifiOff,
} from "lucide-react";

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
}

export function Sidebar({ collapsed, onToggle }: SidebarProps) {
  const { scanHistory, setScanHistory, ollamaStatus, setOllamaStatus } = useScanStore();
  const [activeSection, setActiveSection] = useState<"dashboard" | "history" | "settings">("dashboard");

  // Poll Ollama health
  useEffect(() => {
    const check = async () => {
      try {
        const h = await nmapApi.listScans();
        // Just check API health implicitly
      } catch {}
    };

    const checkOllama = async () => {
      try {
        const res = await fetch("http://localhost:8000/health").then(r => r.json());
        const ok = res?.ollama?.status === "ok";
        setOllamaStatus(ok ? "ok" : "error", res?.ollama?.models ?? []);
      } catch {
        setOllamaStatus("error");
      }
    };

    checkOllama();
    const interval = setInterval(checkOllama, 15000);
    return () => clearInterval(interval);
  }, [setOllamaStatus]);

  // Load scan history
  useEffect(() => {
    nmapApi.listScans().then(setScanHistory).catch(() => {});
    const interval = setInterval(() => {
      nmapApi.listScans().then(setScanHistory).catch(() => {});
    }, 5000);
    return () => clearInterval(interval);
  }, [setScanHistory]);

  return (
    <aside className={cn(
      "flex flex-col h-full bg-slate-900 border-r border-slate-800 transition-all duration-200",
      collapsed ? "w-14" : "w-56"
    )}>
      {/* Logo */}
      <div className="flex items-center gap-2.5 px-3 py-4 border-b border-slate-800">
        <div className="w-8 h-8 rounded-lg bg-cyan-600/20 border border-cyan-700/40 flex items-center justify-center shrink-0">
          <Shield className="w-4 h-4 text-cyan-400" />
        </div>
        {!collapsed && (
          <div className="min-w-0">
            <div className="text-sm font-bold text-slate-100">NmapSLM</div>
            <div className="text-[10px] text-slate-500">v1.0.0</div>
          </div>
        )}
        <button
          onClick={onToggle}
          className="ml-auto text-slate-600 hover:text-slate-300 transition-colors"
        >
          {collapsed
            ? <ChevronRight className="w-4 h-4" />
            : <ChevronLeft className="w-4 h-4" />}
        </button>
      </div>

      {/* Nav */}
      <nav className="flex-1 py-3 space-y-0.5 px-2 overflow-y-auto">
        <NavItem
          icon={LayoutDashboard}
          label="Dashboard"
          active={activeSection === "dashboard"}
          collapsed={collapsed}
          onClick={() => setActiveSection("dashboard")}
        />
        <NavItem
          icon={History}
          label="Riwayat Scan"
          active={activeSection === "history"}
          collapsed={collapsed}
          onClick={() => setActiveSection("history")}
          badge={scanHistory.length > 0 ? String(scanHistory.length) : undefined}
        />
        <NavItem
          icon={Settings2}
          label="Pengaturan"
          active={activeSection === "settings"}
          collapsed={collapsed}
          onClick={() => setActiveSection("settings")}
        />

        {/* History list */}
        {!collapsed && activeSection === "history" && scanHistory.length > 0 && (
          <div className="mt-2 space-y-1">
            <div className="text-[10px] uppercase tracking-wider text-slate-600 px-3 py-1">
              Terbaru
            </div>
            {scanHistory.slice(0, 10).map((scan) => {
              const statusCfg = STATUS_CONFIG[scan.status as keyof typeof STATUS_CONFIG] ?? STATUS_CONFIG.pending;
              return (
                <div
                  key={scan.scan_id}
                  className="px-3 py-2 rounded-lg hover:bg-slate-800 cursor-pointer transition-colors"
                >
                  <div className="flex items-center gap-1.5 mb-0.5">
                    <div className={cn("w-1.5 h-1.5 rounded-full shrink-0",
                      scan.status === "completed" ? "bg-green-400" :
                      scan.status === "running" ? "bg-blue-400 animate-pulse" :
                      scan.status === "failed" ? "bg-red-400" : "bg-slate-500"
                    )} />
                    <span className={cn("text-[10px] font-medium", statusCfg.color)}>
                      {statusCfg.label}
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 font-mono truncate leading-tight">
                    {truncate(scan.command, 28)}
                  </p>
                  <p className="text-[10px] text-slate-600 mt-0.5">
                    {scan.hosts_count} host · {formatDate(scan.start_time)}
                  </p>
                </div>
              );
            })}
          </div>
        )}
      </nav>

      {/* Ollama status */}
      <div className={cn(
        "px-3 py-3 border-t border-slate-800",
        collapsed ? "flex justify-center" : ""
      )}>
        {collapsed ? (
          <div className={cn(
            "w-2 h-2 rounded-full",
            ollamaStatus === "ok" ? "bg-green-400" :
            ollamaStatus === "error" ? "bg-red-500" : "bg-slate-600"
          )} />
        ) : (
          <div className="flex items-center gap-2">
            {ollamaStatus === "ok"
              ? <Wifi className="w-3.5 h-3.5 text-green-400 shrink-0" />
              : <WifiOff className="w-3.5 h-3.5 text-red-400 shrink-0" />}
            <div className="min-w-0">
              <div className="text-xs text-slate-400">Ollama</div>
              <div className={cn("text-[10px]",
                ollamaStatus === "ok" ? "text-green-400" : "text-red-400"
              )}>
                {ollamaStatus === "ok" ? "Terhubung" : ollamaStatus === "error" ? "Terputus" : "Memeriksa…"}
              </div>
            </div>
          </div>
        )}
      </div>
    </aside>
  );
}

function NavItem({
  icon: Icon, label, active, collapsed, onClick, badge,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  active: boolean;
  collapsed: boolean;
  onClick: () => void;
  badge?: string;
}) {
  return (
    <button
      onClick={onClick}
      title={collapsed ? label : undefined}
      className={cn(
        "w-full flex items-center gap-2.5 px-2 py-2 rounded-lg transition-colors text-left",
        active
          ? "bg-cyan-700/20 text-cyan-300"
          : "text-slate-500 hover:text-slate-200 hover:bg-slate-800",
        collapsed && "justify-center"
      )}
    >
      <Icon className="w-4 h-4 shrink-0" />
      {!collapsed && (
        <>
          <span className="text-sm flex-1">{label}</span>
          {badge && (
            <span className="text-[10px] bg-slate-700 text-slate-400 px-1.5 py-0.5 rounded-full">
              {badge}
            </span>
          )}
        </>
      )}
    </button>
  );
}
