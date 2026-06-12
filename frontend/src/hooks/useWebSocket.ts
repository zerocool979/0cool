"use client";

import { useEffect, useRef, useCallback, useState } from "react";
import type { WebSocketEvent } from "@/types";
import { useScanStore } from "@/store/scanStore";
import { toast } from "sonner";

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";

export function useScanWebSocket() {
  const wsRef = useRef<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>();
  const reconnectCount = useRef(0);

  const {
    setScanStarted,
    addProgressLine,
    setScanComplete,
    setScanFailed,
    setScanAnalysis,
    setIsAnalyzing,
  } = useScanStore();

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const ws = new WebSocket(`${WS_URL}/api/v1/ws/scan`);
    wsRef.current = ws;

    ws.onopen = () => {
      setIsConnected(true);
      reconnectCount.current = 0;
    };

    ws.onclose = () => {
      setIsConnected(false);
      wsRef.current = null;
      // Auto-reconnect with backoff
      const delay = Math.min(1000 * Math.pow(2, reconnectCount.current), 30000);
      reconnectCount.current++;
      reconnectTimeoutRef.current = setTimeout(connect, delay);
    };

    ws.onerror = () => {
      // Will trigger onclose
    };

    ws.onmessage = (event) => {
      try {
        const data: WebSocketEvent = JSON.parse(event.data);
        handleEvent(data);
      } catch {
        // ignore
      }
    };
  }, []);

  const handleEvent = useCallback((event: WebSocketEvent) => {
    switch (event.type) {
      case "scan_started":
        setScanStarted(event.scan_id);
        break;

      case "progress":
        if (event.line) addProgressLine(event.line);
        break;

      case "scan_complete":
        setScanComplete(event.result);
        toast.success(`Scan selesai: ${event.hosts_count} host ditemukan`);
        break;

      case "scan_failed":
        setScanFailed(event.error);
        toast.error(`Scan gagal: ${event.error}`);
        break;

      case "analyzing":
        setIsAnalyzing(true);
        break;

      case "analysis_complete":
        setScanAnalysis(event.analysis);
        toast.success("Analisis AI selesai");
        break;

      case "analysis_error":
        setIsAnalyzing(false);
        toast.warning(`Analisis gagal: ${event.message}`);
        break;

      case "error":
        toast.error(event.message);
        break;
    }
  }, [setScanStarted, addProgressLine, setScanComplete, setScanFailed, setScanAnalysis, setIsAnalyzing]);

  const sendScan = useCallback((command: string) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      toast.error("WebSocket tidak terhubung");
      return false;
    }
    wsRef.current.send(JSON.stringify({ type: "scan", command }));
    return true;
  }, []);

  const cancelScan = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "cancel" }));
    }
  }, []);

  useEffect(() => {
    connect();
    return () => {
      clearTimeout(reconnectTimeoutRef.current);
      wsRef.current?.close();
    };
  }, [connect]);

  return { isConnected, sendScan, cancelScan };
}


export function useChatWebSocket() {
  const wsRef = useRef<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>();

  const {
    addChatMessage,
    updateChatMessage,
    setChatSessionId,
    setIsChatLoading,
  } = useScanStore();

  const currentMsgIdRef = useRef<string | null>(null);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const ws = new WebSocket(`${WS_URL}/api/v1/ws/chat`);
    wsRef.current = ws;

    ws.onopen = () => setIsConnected(true);

    ws.onclose = () => {
      setIsConnected(false);
      wsRef.current = null;
      reconnectTimeoutRef.current = setTimeout(connect, 3000);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        if (data.type === "connected") {
          setChatSessionId(data.session_id);
        } else if (data.type === "typing") {
          setIsChatLoading(true);
          // Create placeholder message
          const id = addChatMessage({
            role: "assistant",
            content: "",
            timestamp: new Date().toISOString(),
            isStreaming: true,
          });
          currentMsgIdRef.current = id;
        } else if (data.type === "chunk" && currentMsgIdRef.current) {
          updateChatMessage(
            currentMsgIdRef.current,
            // Append chunk to existing content
            (useScanStore.getState().chatMessages.find(m => m.id === currentMsgIdRef.current)?.content || "") + data.content,
            true
          );
        } else if (data.type === "message_complete") {
          if (currentMsgIdRef.current) {
            updateChatMessage(currentMsgIdRef.current, data.full_content, false);
            currentMsgIdRef.current = null;
          }
          setIsChatLoading(false);
        }
      } catch {}
    };
  }, []);

  const sendMessage = useCallback((content: string, context?: string) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      return false;
    }
    addChatMessage({
      role: "user",
      content,
      timestamp: new Date().toISOString(),
    });
    wsRef.current.send(JSON.stringify({ type: "message", content, context }));
    return true;
  }, [addChatMessage]);

  useEffect(() => {
    connect();
    return () => {
      clearTimeout(reconnectTimeoutRef.current);
      wsRef.current?.close();
    };
  }, [connect]);

  return { isConnected, sendMessage };
}
