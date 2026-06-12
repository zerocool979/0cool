"use client";

import { useState } from "react";
import { Sidebar } from "@/components/layout/Sidebar";
import { Header } from "@/components/layout/Header";
import { NmapForm } from "@/components/nmap/NmapForm";
import { ChatPanel } from "@/components/chat/ChatPanel";
import { ResultDashboard } from "@/components/results/ResultDashboard";
import { cn } from "@/lib/utils";
import { PanelLeft, PanelRight, MessageSquare, Terminal } from "lucide-react";

type MobilePanel = "scan" | "results" | "chat";

export default function DashboardPage() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobilePanel, setMobilePanel]           = useState<MobilePanel>("scan");

  return (
    <div className="flex h-screen overflow-hidden bg-slate-950">
      {/* ── Sidebar ──────────────────────────────────────────────────────── */}
      <Sidebar
        collapsed={sidebarCollapsed}
        onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
      />

      {/* ── Main area ────────────────────────────────────────────────────── */}
      <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
        <Header />

        {/* ── Mobile tab bar ─────────────────────────────────────────────── */}
        <div className="flex md:hidden border-b border-slate-800 bg-slate-900 shrink-0">
          {(
            [
              { id: "scan",    label: "Scan",     icon: Terminal      },
              { id: "results", label: "Hasil",    icon: PanelLeft     },
              { id: "chat",    label: "AI Chat",  icon: MessageSquare },
            ] as { id: MobilePanel; label: string; icon: React.ComponentType<{ className?: string }> }[]
          ).map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setMobilePanel(id)}
              className={cn(
                "flex-1 flex flex-col items-center gap-0.5 py-2 text-[10px] transition-colors",
                mobilePanel === id
                  ? "text-cyan-400 border-b-2 border-cyan-400"
                  : "text-slate-500"
              )}
            >
              <Icon className="w-4 h-4" />
              {label}
            </button>
          ))}
        </div>

        {/* ── Three-column grid (desktop) / single panel (mobile) ────────── */}
        <div className="flex flex-1 min-h-0 overflow-hidden">

          {/* Left — Nmap scanner */}
          <div className={cn(
            "flex flex-col border-r border-slate-800 overflow-hidden",
            /* desktop: fixed width */   "md:w-[320px] lg:w-[360px] xl:w-[400px] md:flex",
            /* mobile: full or hidden */ mobilePanel === "scan" ? "flex flex-1" : "hidden"
          )}>
            <NmapForm />
          </div>

          {/* Centre — Results */}
          <div className={cn(
            "flex flex-col flex-1 min-w-0 overflow-hidden",
            mobilePanel === "results" ? "flex" : "hidden md:flex"
          )}>
            <ResultDashboard />
          </div>

          {/* Right — AI Chat */}
          <div className={cn(
            "flex flex-col border-l border-slate-800 overflow-hidden",
            /* desktop */  "md:w-[300px] lg:w-[340px] xl:w-[380px] md:flex",
            /* mobile */   mobilePanel === "chat" ? "flex flex-1" : "hidden"
          )}>
            <ChatPanel />
          </div>
        </div>
      </div>
    </div>
  );
}
