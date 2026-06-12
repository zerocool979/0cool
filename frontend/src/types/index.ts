// ===== Enums =====

export type ScanStatus =
  | "pending"
  | "running"
  | "completed"
  | "failed"
  | "cancelled";

export type RiskLevel = "critical" | "high" | "medium" | "low" | "info";

export type MessageRole = "user" | "assistant" | "system";

export type ExportFormat = "pdf" | "md" | "json";

// ===== Nmap Models =====

export interface ServiceInfo {
  name: string;
  product: string;
  version: string;
  extra_info: string;
  cpe: string[];
}

export interface ScriptOutput {
  id: string;
  output: string;
}

export interface PortInfo {
  port: number;
  protocol: string;
  state: string;
  reason: string;
  service: ServiceInfo;
  scripts: ScriptOutput[];
}

export interface OSMatch {
  name: string;
  accuracy: number;
  line: string;
}

export interface HostInfo {
  address: string;
  hostname: string;
  status: string;
  os_matches: OSMatch[];
  ports: PortInfo[];
  uptime: string | null;
  distance: number | null;
}

export interface NmapRunStats {
  elapsed: number;
  hosts_up: number;
  hosts_down: number;
  hosts_total: number;
}

export interface NmapScanResult {
  scan_id: string;
  command: string;
  start_time: string;
  end_time: string | null;
  status: ScanStatus;
  hosts: HostInfo[];
  raw_output: string;
  run_stats: NmapRunStats;
  error_message: string | null;
}

// ===== Analysis Models =====

export interface PortRisk {
  port: number;
  protocol: string;
  service: string;
  risk_level: RiskLevel;
  description: string;
  recommendation: string;
}

export interface ScanAnalysis {
  scan_id: string;
  summary: string;
  total_hosts: number;
  open_ports_count: number;
  risk_assessment: RiskLevel;
  port_risks: PortRisk[];
  vulnerabilities: string[];
  ai_analysis: string;
  recommendations: string[];
  next_commands: string[];
  legal_notice: string;
  report_markdown: string;
  generated_at: string;
}

// ===== Chat Models =====

export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  timestamp: string;
  isStreaming?: boolean;
}

export interface ChatSession {
  session_id: string;
  messages: ChatMessage[];
}

// ===== API Request/Response Models =====

export interface ScanRequest {
  command: string;
}

export interface ScanResponse {
  scan_id: string;
  status: ScanStatus;
  message: string;
}

export interface ScanStatusResponse {
  scan_id: string;
  status: ScanStatus;
  progress: number;
  message: string;
  result: NmapScanResult | null;
  analysis: ScanAnalysis | null;
}

export interface ChatRequest {
  message: string;
  session_id?: string;
  context?: string;
  scan_id?: string;
}

// ===== WebSocket Event Types =====

export type WebSocketEvent =
  | { type: "connected"; message: string }
  | { type: "scan_started"; scan_id: string; command: string; message: string }
  | { type: "progress"; scan_id: string; line: string; status?: string }
  | { type: "scan_complete"; scan_id: string; hosts_count: number; result: NmapScanResult }
  | { type: "scan_failed"; scan_id: string; error: string }
  | { type: "analyzing"; message: string }
  | { type: "analysis_complete"; scan_id: string; analysis: ScanAnalysis }
  | { type: "analysis_error"; message: string }
  | { type: "error"; message: string }
  | { type: "cancelled"; scan_id: string }
  | { type: "pong" };

export type ChatWebSocketEvent =
  | { type: "connected"; session_id: string; message: string }
  | { type: "typing"; session_id: string }
  | { type: "chunk"; session_id: string; content: string }
  | { type: "message_complete"; session_id: string; full_content: string }
  | { type: "pong" };

// ===== UI State =====

export interface ScanState {
  currentScanId: string | null;
  currentScan: NmapScanResult | null;
  currentAnalysis: ScanAnalysis | null;
  scanStatus: ScanStatus | null;
  progressLines: string[];
  isAnalyzing: boolean;
  scanHistory: NmapScanResult[];
  activeTab: "raw" | "analysis" | "recommendations" | "report" | "download";
}

export interface AppConfig {
  backendUrl: string;
  wsUrl: string;
  ollamaModel: string;
}

// ===== Helpers =====

export const RISK_CONFIG: Record<RiskLevel, { label: string; color: string; bg: string; border: string; icon: string }> = {
  critical: { label: "KRITIS", color: "text-red-400", bg: "bg-red-950/50", border: "border-red-800", icon: "🔴" },
  high:     { label: "TINGGI", color: "text-orange-400", bg: "bg-orange-950/50", border: "border-orange-800", icon: "🟠" },
  medium:   { label: "SEDANG", color: "text-yellow-400", bg: "bg-yellow-950/50", border: "border-yellow-800", icon: "🟡" },
  low:      { label: "RENDAH", color: "text-green-400", bg: "bg-green-950/50", border: "border-green-800", icon: "🟢" },
  info:     { label: "INFO", color: "text-blue-400", bg: "bg-blue-950/50", border: "border-blue-800", icon: "ℹ️" },
};

export const STATUS_CONFIG: Record<ScanStatus, { label: string; color: string }> = {
  pending:   { label: "Menunggu", color: "text-slate-400" },
  running:   { label: "Berjalan", color: "text-blue-400" },
  completed: { label: "Selesai", color: "text-green-400" },
  failed:    { label: "Gagal", color: "text-red-400" },
  cancelled: { label: "Dibatalkan", color: "text-yellow-400" },
};
