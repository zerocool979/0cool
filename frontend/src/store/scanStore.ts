import { create } from "zustand";
import type { NmapScanResult, ScanAnalysis, ScanStatus, ChatMessage, AIProvider } from "@/types";
import { nanoid } from "@/lib/utils";
interface ScanStore {
  currentScanId: string | null;
  currentScan: NmapScanResult | null;
  currentAnalysis: ScanAnalysis | null;
  scanStatus: ScanStatus | null;
  progressLines: string[];
  isAnalyzing: boolean;
  activeTab: "raw" | "analysis" | "recommendations" | "report" | "download";

  chatMessages: ChatMessage[];
  chatSessionId: string | null;
  isChatLoading: boolean;

  // AI Provider
  activeProvider: AIProvider;
  defaultProvider: AIProvider;
  providerAvailability: {
    gemini: "unknown" | "ok" | "error";
    slm: "unknown" | "ok" | "error";
  };
  setActiveProvider: (p: AIProvider) => void;
  setDefaultProvider: (p: AIProvider) => void;
  setProviderAvailability: (p: AIProvider, status: "unknown" | "ok" | "error") => void;

  scanHistory: Array<{
    scan_id: string;
    command: string;
    status: string;
    start_time: string;
    hosts_count: number;
  }>;

  ollamaStatus: "unknown" | "ok" | "error";
  ollamaModels: string[];

  setScanStarted: (scanId: string) => void;
  addProgressLine: (line: string) => void;
  setScanComplete: (scan: NmapScanResult) => void;
  setScanFailed: (error: string) => void;
  setScanAnalysis: (analysis: ScanAnalysis) => void;
  setIsAnalyzing: (v: boolean) => void;
  setActiveTab: (tab: ScanStore["activeTab"]) => void;
  clearCurrentScan: () => void;

  addChatMessage: (msg: Omit<ChatMessage, "id">) => string;
  updateChatMessage: (id: string, content: string, isStreaming?: boolean) => void;
  clearChatHistory: () => void;
  setChatSessionId: (id: string) => void;
  setIsChatLoading: (v: boolean) => void;

  setScanHistory: (history: ScanStore["scanHistory"]) => void;
  setOllamaStatus: (status: "unknown" | "ok" | "error", models?: string[]) => void;
}

export const useScanStore = create<ScanStore>((set) => ({
  currentScanId: null,
  currentScan: null,
  currentAnalysis: null,
  scanStatus: null,
  progressLines: [],
  isAnalyzing: false,
  activeTab: "raw",

  chatMessages: [],
  chatSessionId: null,
  isChatLoading: false,

  activeProvider: "gemini",
  defaultProvider: "gemini",
  providerAvailability: { gemini: "unknown", slm: "unknown" },
  setActiveProvider: (p) => set({ activeProvider: p }),
  setDefaultProvider: (p) => set({ defaultProvider: p, activeProvider: p }),
  setProviderAvailability: (p, status) =>
    set((s) => ({ providerAvailability: { ...s.providerAvailability, [p]: status } })),

  scanHistory: [],
  ollamaStatus: "unknown",
  ollamaModels: [],

  setScanStarted: (scanId) =>
    set({ currentScanId: scanId, scanStatus: "running", progressLines: [], currentScan: null, currentAnalysis: null, activeTab: "raw" }),

  addProgressLine: (line) =>
    set((s) => ({ progressLines: [...s.progressLines.slice(-200), line] })),

  setScanComplete: (scan) =>
    set({ currentScan: scan, scanStatus: "completed", activeTab: "raw" }),

  setScanFailed: (_) => set({ scanStatus: "failed" }),

  setScanAnalysis: (analysis) =>
    set({ currentAnalysis: analysis, isAnalyzing: false, activeTab: "analysis" }),

  setIsAnalyzing: (v) => set({ isAnalyzing: v }),
  setActiveTab: (tab) => set({ activeTab: tab }),

  clearCurrentScan: () =>
    set({ currentScanId: null, currentScan: null, currentAnalysis: null, scanStatus: null, progressLines: [], isAnalyzing: false, activeTab: "raw" }),

  addChatMessage: (msg) => {
    const id = nanoid();
    set((s) => ({ chatMessages: [...s.chatMessages, { ...msg, id }] }));
    return id;
  },

  updateChatMessage: (id, content, isStreaming) =>
    set((s) => ({
      chatMessages: s.chatMessages.map((m) =>
        m.id === id ? { ...m, content, isStreaming: isStreaming ?? false } : m
      ),
    })),

  clearChatHistory: () => set({ chatMessages: [], chatSessionId: null }),
  setChatSessionId: (id) => set({ chatSessionId: id }),
  setIsChatLoading: (v) => set({ isChatLoading: v }),
  setScanHistory: (history) => set({ scanHistory: history }),
  setOllamaStatus: (status, models = []) => set({ ollamaStatus: status, ollamaModels: models }),
}));
