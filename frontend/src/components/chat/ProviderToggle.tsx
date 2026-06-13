"use client";

import { useEffect, useState } from "react";
import { useScanStore } from "@/store/scanStore";
import { chatApi } from "@/lib/api";
import { PROVIDER_CONFIG, type AIProvider } from "@/types";
import { cn } from "@/lib/utils";
import { Loader2, Wifi, WifiOff, ChevronDown } from "lucide-react";

export function ProviderToggle() {
  const {
    activeProvider,
    defaultProvider,
    providerAvailability,
    setActiveProvider,
    setDefaultProvider,
    setProviderAvailability,
  } = useScanStore();

  const [open, setOpen]       = useState(false);
  const [loading, setLoading] = useState(true);

  // On mount: fetch provider list from server and probe availability
  useEffect(() => {
    let cancelled = false;
    const init = async () => {
      try {
        const p = await chatApi.listProviders();
        if (cancelled) return;
        setDefaultProvider(p.default as AIProvider);

        const h = await chatApi.checkHealth();
        if (cancelled) return;
        setProviderAvailability("gemini", h.gemini.status === "ok" ? "ok" : "error");
        setProviderAvailability("slm",    h.slm.status    === "ok" ? "ok" : "error");
      } catch {
        setProviderAvailability("gemini", "error");
        setProviderAvailability("slm",    "error");
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    init();
    return () => { cancelled = true; };
  }, []);

  const cfg = PROVIDER_CONFIG[activeProvider];
  const availability = providerAvailability[activeProvider];

  const StatusIcon = () => {
    if (loading)              return <Loader2 className="w-3 h-3 animate-spin" />;
    if (availability === "ok")   return <Wifi    className="w-3 h-3 text-green-400" />;
    if (availability === "error") return <WifiOff className="w-3 h-3 text-red-400" />;
    return <Loader2 className="w-3 h-3 animate-spin opacity-50" />;
  };

  return (
    <div className="relative">
      {/* Toggle pill */}
      <button
        onClick={() => setOpen(!open)}
        className={cn(
          "flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-xs font-medium transition-colors",
          cfg.bg, cfg.border, cfg.color,
          "hover:brightness-110"
        )}
      >
        <span>{cfg.icon}</span>
        <span>{cfg.label}</span>
        <StatusIcon />
        <ChevronDown className={cn("w-3 h-3 transition-transform", open && "rotate-180")} />
      </button>

      {/* Dropdown */}
      {open && (
        <>
          {/* backdrop */}
          <div
            className="fixed inset-0 z-40"
            onClick={() => setOpen(false)}
          />
          <div className="absolute right-0 top-full mt-1.5 z-50 w-64 bg-slate-900 border border-slate-700 rounded-xl shadow-xl overflow-hidden">
            <div className="px-3 py-2 border-b border-slate-800 text-[10px] uppercase tracking-wider text-slate-500">
              AI Provider
            </div>

            {(["gemini", "slm"] as AIProvider[]).map((id) => {
              const pcfg = PROVIDER_CONFIG[id];
              const avail = providerAvailability[id];
              const isActive = activeProvider === id;
              const isDefault = defaultProvider === id;

              return (
                <button
                  key={id}
                  onClick={() => { setActiveProvider(id); setOpen(false); }}
                  className={cn(
                    "w-full text-left px-3 py-3 flex items-start gap-3 transition-colors",
                    isActive ? "bg-slate-800" : "hover:bg-slate-800/60"
                  )}
                >
                  {/* color swatch */}
                  <div className={cn(
                    "w-7 h-7 rounded-lg flex items-center justify-center text-base flex-shrink-0 mt-0.5 border",
                    pcfg.bg, pcfg.border
                  )}>
                    {pcfg.icon}
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className={cn("text-sm font-semibold", pcfg.color)}>
                        {pcfg.label}
                      </span>
                      {isDefault && (
                        <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-slate-700 text-slate-400 border border-slate-600">
                          DEFAULT
                        </span>
                      )}
                    </div>
                    <ProviderSubtitle id={id} />
                    <div className="mt-1 flex items-center gap-1">
                      {avail === "ok"      && <Wifi    className="w-3 h-3 text-green-400" />}
                      {avail === "error"   && <WifiOff className="w-3 h-3 text-red-400"   />}
                      {avail === "unknown" && <Loader2 className="w-3 h-3 text-slate-500 animate-spin" />}
                      <span className={cn(
                        "text-[10px]",
                        avail === "ok"    ? "text-green-400" :
                        avail === "error" ? "text-red-400"   : "text-slate-500"
                      )}>
                        {avail === "ok" ? "Tersedia" : avail === "error" ? "Tidak tersedia" : "Memeriksa…"}
                      </span>
                    </div>
                  </div>

                  {isActive && (
                    <div className="w-1.5 h-1.5 rounded-full bg-cyan-400 mt-1.5 flex-shrink-0" />
                  )}
                </button>
              );
            })}

            <div className="px-3 py-2 border-t border-slate-800 text-[10px] text-slate-600 leading-relaxed">
              Gemini memerlukan internet + API key.<br />
              SLM berjalan 100% offline via Ollama.
            </div>
          </div>
        </>
      )}
    </div>
  );
}

function ProviderSubtitle({ id }: { id: AIProvider }) {
  if (id === "gemini") {
    return <p className="text-[10px] text-slate-500 mt-0.5">Google Gemini 2.0 Flash · Cloud</p>;
  }
  return <p className="text-[10px] text-slate-500 mt-0.5">Ollama · QwenNmap · Offline</p>;
}
