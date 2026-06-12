"use client";

import { useState } from "react";
import { useScanStore } from "@/store/scanStore";
import { cn, copyToClipboard, formatDuration } from "@/lib/utils";
import {
  Copy, Check, ChevronDown, ChevronRight,
  Server, Globe, Cpu, Shield,
} from "lucide-react";
import type { HostInfo, PortInfo } from "@/types";

export function RawOutput() {
  const { currentScan } = useScanStore();
  const [activeView, setActiveView] = useState<"structured" | "raw">("structured");
  const [copied, setCopied] = useState(false);

  if (!currentScan) return null;

  const handleCopy = () => {
    copyToClipboard(currentScan.raw_output).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  const totalOpen = currentScan.hosts.reduce(
    (n, h) => n + h.ports.filter((p) => p.state === "open").length,
    0
  );

  return (
    <div className="flex flex-col h-full">
      {/* sub-toolbar */}
      <div className="flex items-center gap-2 px-4 py-2 border-b border-slate-800 shrink-0">
        <div className="flex rounded-lg border border-slate-700 overflow-hidden text-xs">
          {(["structured", "raw"] as const).map((v) => (
            <button
              key={v}
              onClick={() => setActiveView(v)}
              className={cn(
                "px-3 py-1.5 capitalize transition-colors",
                activeView === v
                  ? "bg-slate-700 text-slate-100"
                  : "text-slate-500 hover:text-slate-300"
              )}
            >
              {v === "structured" ? "Terstruktur" : "Raw Text"}
            </button>
          ))}
        </div>

        {/* stats */}
        <div className="flex gap-3 ml-2 text-xs text-slate-500">
          <span><span className="text-slate-300 font-medium">{currentScan.hosts.length}</span> host</span>
          <span><span className="text-green-400 font-medium">{totalOpen}</span> open</span>
          <span className="hidden sm:inline">
            <span className="text-slate-300 font-medium">
              {formatDuration(currentScan.run_stats.elapsed)}
            </span>
          </span>
        </div>

        <button
          onClick={handleCopy}
          className="ml-auto flex items-center gap-1 text-xs text-slate-500 hover:text-slate-300 transition-colors"
        >
          {copied ? <Check className="w-3.5 h-3.5 text-green-400" /> : <Copy className="w-3.5 h-3.5" />}
          <span className="hidden sm:inline">{copied ? "Disalin" : "Salin"}</span>
        </button>
      </div>

      <div className="flex-1 overflow-y-auto">
        {activeView === "structured" ? (
          <StructuredView hosts={currentScan.hosts} />
        ) : (
          <RawTextView raw={currentScan.raw_output} />
        )}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────
// Structured host cards
// ─────────────────────────────────────────────────────────────────
function StructuredView({ hosts }: { hosts: HostInfo[] }) {
  if (hosts.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-slate-600 text-sm">
        Tidak ada host ditemukan
      </div>
    );
  }

  return (
    <div className="p-4 space-y-3">
      {hosts.map((host) => (
        <HostCard key={host.address} host={host} />
      ))}
    </div>
  );
}

function HostCard({ host }: { host: HostInfo }) {
  const [open, setOpen] = useState(true);
  const openPorts = host.ports.filter((p) => p.state === "open");
  const filteredPorts = host.ports.filter((p) => p.state.includes("filtered"));

  return (
    <div className="border border-slate-700/60 rounded-xl overflow-hidden bg-slate-800/40">
      {/* host header */}
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center gap-3 px-4 py-3 hover:bg-slate-800/60 transition-colors text-left"
      >
        <div className={cn(
          "w-2 h-2 rounded-full shrink-0",
          host.status === "up" ? "bg-green-400" : "bg-red-500"
        )} />
        <Server className="w-4 h-4 text-cyan-500 shrink-0" />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-semibold text-slate-100 font-mono">{host.address}</span>
            {host.hostname && (
              <span className="text-xs text-slate-400 flex items-center gap-1">
                <Globe className="w-3 h-3" /> {host.hostname}
              </span>
            )}
            {host.os_matches?.[0] && (
              <span className="text-xs text-slate-500 flex items-center gap-1">
                <Cpu className="w-3 h-3" />
                {host.os_matches[0].name.split(" ").slice(0, 3).join(" ")}
                <span className="text-slate-600">({host.os_matches[0].accuracy}%)</span>
              </span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0 text-xs">
          <span className="text-green-400 font-medium">{openPorts.length} open</span>
          {filteredPorts.length > 0 && (
            <span className="text-yellow-600">{filteredPorts.length} filtered</span>
          )}
          {open ? <ChevronDown className="w-3.5 h-3.5 text-slate-500" /> : <ChevronRight className="w-3.5 h-3.5 text-slate-500" />}
        </div>
      </button>

      {/* port table */}
      {open && host.ports.length > 0 && (
        <div className="border-t border-slate-700/60">
          <table className="w-full text-xs">
            <thead>
              <tr className="text-slate-500 border-b border-slate-700/40">
                <th className="text-left px-4 py-2 font-medium">PORT</th>
                <th className="text-left px-4 py-2 font-medium">PROTOKOL</th>
                <th className="text-left px-4 py-2 font-medium">STATE</th>
                <th className="text-left px-4 py-2 font-medium">LAYANAN</th>
                <th className="text-left px-4 py-2 font-medium hidden sm:table-cell">VERSI</th>
              </tr>
            </thead>
            <tbody>
              {host.ports.map((port) => (
                <PortRow key={`${port.port}-${port.protocol}`} port={port} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function PortRow({ port }: { port: PortInfo }) {
  const stateColor = {
    open: "text-green-400",
    closed: "text-slate-600",
    filtered: "text-yellow-500",
  }[port.state] ?? "text-slate-500";

  const svc = port.service;
  const version = [svc.product, svc.version].filter(Boolean).join(" ");

  return (
    <tr className="border-b border-slate-800/60 hover:bg-slate-800/30 transition-colors">
      <td className="px-4 py-2 font-mono font-semibold text-cyan-300">{port.port}</td>
      <td className="px-4 py-2 text-slate-400">{port.protocol.toUpperCase()}</td>
      <td className={cn("px-4 py-2 font-medium", stateColor)}>{port.state}</td>
      <td className="px-4 py-2 text-slate-300">{svc.name || "-"}</td>
      <td className="px-4 py-2 text-slate-500 hidden sm:table-cell max-w-[180px] truncate">
        {version || "-"}
      </td>
    </tr>
  );
}

// ─────────────────────────────────────────────────────────────────
// Raw text view
// ─────────────────────────────────────────────────────────────────
function RawTextView({ raw }: { raw: string }) {
  if (!raw) {
    return (
      <div className="flex items-center justify-center h-full text-slate-600 text-sm">
        Tidak ada output mentah
      </div>
    );
  }

  return (
    <div className="p-4">
      <pre className="font-mono text-xs text-slate-300 whitespace-pre-wrap leading-relaxed">
        {raw.split("\n").map((line, i) => {
          const isOpen     = /open/.test(line) && !/not open/.test(line);
          const isFiltered = /filtered/.test(line);
          const isWarning  = /warning|error/i.test(line);
          return (
            <span
              key={i}
              className={cn(
                "block",
                isOpen     && "text-green-400",
                isFiltered && "text-yellow-500",
                isWarning  && "text-amber-400",
              )}
            >
              {line || " "}
            </span>
          );
        })}
      </pre>
    </div>
  );
}
