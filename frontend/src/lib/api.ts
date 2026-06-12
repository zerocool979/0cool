import type {
  ScanRequest,
  ScanResponse,
  ScanStatusResponse,
  ScanAnalysis,
  ChatRequest,
  ChatResponse,
  ExportFormat,
  NmapScanResult,
} from "@/types";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

class ApiError extends Error {
  constructor(
    public status: number,
    public detail: string
  ) {
    super(detail);
    this.name = "ApiError";
  }
}

async function request<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const url = `${BASE_URL}${path}`;
  const res = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
    ...options,
  });

  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const err = await res.json();
      detail = err.detail || detail;
    } catch {}
    throw new ApiError(res.status, detail);
  }

  const contentType = res.headers.get("content-type");
  if (contentType?.includes("application/json")) {
    return res.json();
  }

  return res as unknown as T;
}

// ===== Nmap API =====

export const nmapApi = {
  startScan: (req: ScanRequest) =>
    request<ScanResponse>("/nmap/scan", {
      method: "POST",
      body: JSON.stringify(req),
    }),

  getScanStatus: (scanId: string) =>
    request<ScanStatusResponse>(`/nmap/scan/${scanId}/status`),

  analyzeScan: (scanId: string) =>
    request<ScanAnalysis>(`/nmap/scan/${scanId}/analyze`, {
      method: "POST",
    }),

  listScans: () =>
    request<Array<{ scan_id: string; command: string; status: string; start_time: string; hosts_count: number }>>(
      "/nmap/scans"
    ),

  deleteScan: (scanId: string) =>
    request<{ message: string }>(`/nmap/scan/${scanId}`, { method: "DELETE" }),

  downloadReport: async (
    scanId: string,
    format: ExportFormat,
    includeRaw = true
  ): Promise<{ blob: Blob; filename: string }> => {
    const url = `${BASE_URL}/nmap/scan/${scanId}/report`;
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        scan_id: scanId,
        format,
        include_raw: includeRaw,
        include_analysis: true,
        include_recommendations: true,
      }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new ApiError(res.status, err.detail || "Download gagal");
    }

    const contentDisposition = res.headers.get("content-disposition") || "";
    const filenameMatch = contentDisposition.match(/filename="?([^"]+)"?/);
    const filename = filenameMatch?.[1] || `nmap_report_${scanId}.${format}`;

    const blob = await res.blob();
    return { blob, filename };
  },
};

// ===== Chat API =====

export const chatApi = {
  sendMessage: (req: ChatRequest) =>
    request<ChatResponse>("/chat/message", {
      method: "POST",
      body: JSON.stringify(req),
    }),

  streamMessage: (req: ChatRequest): EventSource => {
    // Use fetch with ReadableStream for SSE
    return new EventSource(
      `${BASE_URL}/chat/stream?` + new URLSearchParams({ message: req.message })
    );
  },

  clearSession: (sessionId: string) =>
    request<{ message: string }>(`/chat/session/${sessionId}`, {
      method: "DELETE",
    }),

  checkHealth: () =>
    request<{ status: string; models: string[]; model_available: boolean }>(
      "/chat/health"
    ),
};

// ===== Health API =====

export const healthApi = {
  check: () =>
    request<{ status: string; app: string; version: string; ollama: object }>(
      "/health".replace("/api/v1", "")
    ),
};

// ===== Streaming Chat Helper =====

export async function* streamChatResponse(
  req: ChatRequest
): AsyncGenerator<string> {
  const url = `${BASE_URL}/chat/stream`;
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });

  if (!res.ok || !res.body) {
    throw new ApiError(res.status, "Stream failed");
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let sessionId = "";
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      if (line.startsWith("data: ")) {
        const data = line.slice(6);
        if (data === "[DONE]") return;
        if (!sessionId && !data.includes(" ") && data.length < 50) {
          sessionId = data; // First SSE is session ID
          continue;
        }
        // Unescape newlines
        yield data.replace(/\\n/g, "\n");
      }
    }
  }
}

export { ApiError };
