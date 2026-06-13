"use client";

import { useState, useRef, useEffect, KeyboardEvent } from "react";
import { Send, Bot, User, Trash2, Wifi, WifiOff, Loader2, Copy, Check } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useScanStore } from "@/store/scanStore";
import { useChatWebSocket } from "@/hooks/useWebSocket";
import { cn, copyToClipboard, formatDate } from "@/lib/utils";
import type { ChatMessage } from "@/types";

const QUICK_PROMPTS = [
  "Apa itu Nmap?",
  "Bagaimana cara scan yang aman?",
  "Jelaskan UU ITE Pasal 30",
  "Port apa yang paling berbahaya?",
  "Apa itu CVE?",
];

export function ChatPanel() {
  const [input, setInput] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const { chatMessages, isChatLoading, clearChatHistory, currentScan } = useScanStore();
  const { isConnected, sendMessage } = useChatWebSocket();

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatMessages]);

  const handleSend = () => {
    const text = input.trim();
    if (!text || isChatLoading) return;

    // Build context from current scan if available
    let context: string | undefined;
    if (currentScan) {
      const openPorts = currentScan.hosts.flatMap(h =>
        h.ports.filter(p => p.state === "open").map(p => `${p.port}/${p.protocol} (${p.service.name})`)
      );
      context = `Scan command: ${currentScan.command}\nHost: ${currentScan.hosts.map(h => h.address).join(", ")}\nPort terbuka: ${openPorts.slice(0, 10).join(", ")}`;
    }

    sendMessage(text, context);
    setInput("");

    // Reset textarea height
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    // Auto-resize
    const el = e.target;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 120)}px`;
  };

  return (
    <div className="flex flex-col h-full bg-slate-900">
      {/* Header */}
      <div className="px-4 py-3 border-b border-slate-800 flex items-center gap-2">
        <Bot className="w-4 h-4 text-violet-400" />
        <span className="text-sm font-semibold text-slate-200">AI Assistant</span>
        <span className="text-xs text-slate-500 ml-1">QwenNmap</span>
        <div className="ml-auto flex items-center gap-2">
          {isConnected ? (
            <Wifi className="w-3.5 h-3.5 text-green-400" />
          ) : (
            <WifiOff className="w-3.5 h-3.5 text-red-400" />
          )}
          {chatMessages.length > 0 && (
            <button
              onClick={clearChatHistory}
              className="text-slate-600 hover:text-slate-400 transition-colors"
              title="Hapus riwayat"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-4">
        {chatMessages.length === 0 && (
          <WelcomeScreen onPrompt={(p) => {
            setInput(p);
            textareaRef.current?.focus();
          }} />
        )}

        {chatMessages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}

        {isChatLoading && chatMessages[chatMessages.length - 1]?.role !== "assistant" && (
          <div className="flex gap-2 items-start">
            <div className="w-6 h-6 rounded-full bg-violet-700 flex items-center justify-center shrink-0">
              <Bot className="w-3 h-3 text-white" />
            </div>
            <div className="bg-slate-800 rounded-2xl rounded-tl-sm px-3 py-2">
              <Loader2 className="w-4 h-4 text-violet-400 animate-spin" />
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Quick prompts */}
      {chatMessages.length === 0 && (
        <div className="px-4 pb-2 flex gap-2 overflow-x-auto scrollbar-hide">
          {QUICK_PROMPTS.map((p) => (
            <button
              key={p}
              onClick={() => { setInput(p); textareaRef.current?.focus(); }}
              className="shrink-0 text-xs px-3 py-1.5 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-full text-slate-400 hover:text-slate-200 transition-colors"
            >
              {p}
            </button>
          ))}
        </div>
      )}

      {/* Input */}
      <div className="px-4 pb-4 pt-2 border-t border-slate-800">
        <div className="flex gap-2 items-end">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
            placeholder="Tanya tentang keamanan jaringan... (Enter untuk kirim)"
            rows={1}
            disabled={!isConnected || isChatLoading}
            className={cn(
              "flex-1 bg-slate-800 text-slate-100 text-sm",
              "border border-slate-700 rounded-xl px-3 py-2.5",
              "placeholder:text-slate-500 outline-none resize-none",
              "focus:border-violet-600 focus:ring-1 focus:ring-violet-600/30",
              "transition-colors disabled:opacity-50",
              "min-h-[42px] max-h-[120px]"
            )}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || !isConnected || isChatLoading}
            className={cn(
              "p-2.5 rounded-xl bg-violet-600 hover:bg-violet-500 text-white",
              "transition-colors disabled:opacity-40 disabled:cursor-not-allowed",
              "shrink-0"
            )}
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
        <p className="text-xs text-slate-600 mt-1.5 text-center">
          Shift+Enter untuk baris baru • AI lokal, 100% offline
        </p>
      </div>
    </div>
  );
}

function WelcomeScreen({ onPrompt }: { onPrompt: (p: string) => void }) {
  return (
    <div className="flex flex-col items-center justify-center h-full py-8 text-center gap-4">
      <div className="w-14 h-14 rounded-2xl bg-violet-900/40 border border-violet-700/40 flex items-center justify-center">
        <Bot className="w-7 h-7 text-violet-400" />
      </div>
      <div>
        <h3 className="text-sm font-semibold text-slate-200 mb-1">
          AI Security Assistant
        </h3>
        <p className="text-xs text-slate-500 max-w-[200px] leading-relaxed">
          Tanya apapun tentang keamanan jaringan, analisis nmap, atau hukum UU ITE
        </p>
      </div>
    </div>
  );
}

function MessageBubble({ message }: { message: ChatMessage }) {
  const [copied, setCopied] = useState(false);
  const isUser = message.role === "user";

  const handleCopy = () => {
    copyToClipboard(message.content).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  return (
    <div className={cn("flex gap-2 items-start group", isUser && "flex-row-reverse")}>
      {/* Avatar */}
      <div className={cn(
        "w-6 h-6 rounded-full flex items-center justify-center shrink-0 mt-0.5",
        isUser ? "bg-cyan-700" : "bg-violet-700"
      )}>
        {isUser ? (
          <User className="w-3 h-3 text-white" />
        ) : (
          <Bot className="w-3 h-3 text-white" />
        )}
      </div>

      {/* Bubble */}
      <div className={cn(
        "max-w-[85%] relative",
        isUser ? "items-end" : "items-start"
      )}>
        <div className={cn(
          "rounded-2xl px-3 py-2 text-sm",
          isUser
            ? "bg-cyan-700/30 text-slate-100 rounded-tr-sm"
            : "bg-slate-800 text-slate-200 rounded-tl-sm"
        )}>
          {isUser ? (
            <p className="whitespace-pre-wrap leading-relaxed">{message.content}</p>
          ) : (
            <div className="prose prose-invert prose-sm max-w-none">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  code({ node, className, children, ...props }) {
                    const isBlock = className?.includes("language-");
                    return isBlock ? (
                      <code
                        className={cn(
                          "block bg-slate-950 rounded p-2 text-xs overflow-x-auto font-mono",
                          className
                        )}
                        {...props}
                      >
                        {children}
                      </code>
                    ) : (
                      <code
                        className="bg-slate-700 text-cyan-300 px-1 py-0.5 rounded text-xs font-mono"
                        {...props}
                      >
                        {children}
                      </code>
                    );
                  },
                }}
              >
                {message.content || (message.isStreaming ? "▌" : "")}
              </ReactMarkdown>
            </div>
          )}
        </div>

        {/* Copy button */}
        {!message.isStreaming && message.content && (
          <button
            onClick={handleCopy}
            className="opacity-0 group-hover:opacity-100 absolute -bottom-5 right-0 text-slate-600 hover:text-slate-400 transition-all"
          >
            {copied ? <Check className="w-3 h-3 text-green-400" /> : <Copy className="w-3 h-3" />}
          </button>
        )}
      </div>
    </div>
  );
}
