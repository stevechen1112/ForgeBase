"use client";
import { useEffect, useRef, useState, useCallback } from "react";
import { useAuth } from "@/lib/auth/store";
import { API_BASE, buildApiHeaders } from "@/lib/api/client";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import {
  Bot,
  Send,
  Trash2,
  Loader2,
  RefreshCw,
  Sparkles,
  User,
  AlertCircle,
} from "lucide-react";

// ── Types ─────────────────────────────────────────────────────────────────────

type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
  created_at?: string;
  /** true = optimistic (not yet confirmed by server) */
  pending?: boolean;
  /** true = streaming/thinking animation */
  thinking?: boolean;
};

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatTime(iso?: string): string {
  if (!iso) return "";
  return new Date(iso).toLocaleTimeString("zh-TW", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

/** Very small markdown renderer: bold, inline code, code blocks, bullet lists */
function renderContent(text: string): React.ReactNode {
  const lines = text.split("\n");
  const nodes: React.ReactNode[] = [];

  let i = 0;
  while (i < lines.length) {
    const line = lines[i];

    // Code block
    if (line.startsWith("```")) {
      const lang = line.slice(3).trim();
      const codeLines: string[] = [];
      i++;
      while (i < lines.length && !lines[i].startsWith("```")) {
        codeLines.push(lines[i]);
        i++;
      }
      nodes.push(
        <pre
          key={i}
          className="my-2 rounded-md bg-black/30 p-3 text-xs font-mono overflow-x-auto"
        >
          <code>{codeLines.join("\n")}</code>
        </pre>
      );
    }
    // Bullet list item
    else if (/^[-•*]\s/.test(line.trim())) {
      const items: string[] = [];
      while (i < lines.length && /^[-•*]\s/.test(lines[i].trim())) {
        items.push(lines[i].replace(/^[-•*]\s/, "").trim());
        i++;
      }
      nodes.push(
        <ul key={i} className="my-1 ml-4 list-disc space-y-0.5 text-sm">
          {items.map((item, k) => (
            <li key={k}>{inlineRender(item)}</li>
          ))}
        </ul>
      );
      continue;
    }
    // Heading (## or ###)
    else if (/^#{1,3}\s/.test(line)) {
      const content = line.replace(/^#{1,3}\s/, "");
      nodes.push(
        <p key={i} className="mt-3 mb-1 text-sm font-semibold">
          {inlineRender(content)}
        </p>
      );
    }
    // Horizontal rule
    else if (/^---+$/.test(line.trim())) {
      nodes.push(<hr key={i} className="my-2 border-white/10" />);
    }
    // Empty line → spacing
    else if (line.trim() === "") {
      nodes.push(<div key={i} className="h-1.5" />);
    }
    // Normal paragraph
    else {
      nodes.push(
        <p key={i} className="text-sm leading-relaxed">
          {inlineRender(line)}
        </p>
      );
    }
    i++;
  }
  return <>{nodes}</>;
}

function inlineRender(text: string): React.ReactNode {
  // Split on **bold**, *italic*, `code`
  const parts = text.split(/(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)/g);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**"))
      return <strong key={i}>{part.slice(2, -2)}</strong>;
    if (part.startsWith("*") && part.endsWith("*"))
      return <em key={i}>{part.slice(1, -1)}</em>;
    if (part.startsWith("`") && part.endsWith("`"))
      return (
        <code key={i} className="rounded bg-black/30 px-1 py-0.5 text-xs font-mono">
          {part.slice(1, -1)}
        </code>
      );
    return part;
  });
}

// ── Thinking dots animation ────────────────────────────────────────────────

function ThinkingDots() {
  return (
    <span className="flex items-center gap-1 py-1">
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="h-1.5 w-1.5 rounded-full bg-current opacity-70"
          style={{
            animation: `bounce 1.2s infinite ease-in-out both`,
            animationDelay: `${i * 0.2}s`,
          }}
        />
      ))}
      <style>{`
        @keyframes bounce {
          0%, 80%, 100% { transform: translateY(0); opacity: 0.4; }
          40% { transform: translateY(-5px); opacity: 1; }
        }
      `}</style>
    </span>
  );
}

// ── Suggestion chips ──────────────────────────────────────────────────────

const SUGGESTIONS = [
  "今天有幾個新 RFQ？",
  "目前有哪些熱門訪客？",
  "過去 30 天哪個產品詢問最多？",
  "有哪些 RFQ 超過 24 小時未處理？",
  "本週的漏斗轉換率如何？",
];

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function CopilotChatPage() {
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";

  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [clearConfirm, setClearConfirm] = useState(false);

  const scrollRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // ── Scroll to bottom ──────────────────────────────────────────────────────
  const scrollToBottom = useCallback(() => {
    requestAnimationFrame(() => {
      if (scrollRef.current) {
        scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
      }
    });
  }, []);

  // ── Load history ──────────────────────────────────────────────────────────
  const loadHistory = useCallback(async () => {
    setLoadingHistory(true);
    try {
      const res = await fetch(`${API_BASE}/copilot/chat/history?limit=60`, {
        headers: buildApiHeaders(token),
      });
      if (!res.ok) throw new Error("載入失敗");
      const data = await res.json();
      setMessages(data.data || []);
    } catch {
      // Silent — start fresh
    } finally {
      setLoadingHistory(false);
    }
  }, [token]);

  useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  // ── Send message ──────────────────────────────────────────────────────────
  const send = useCallback(
    async (text: string) => {
      const trimmed = text.trim();
      if (!trimmed || sending) return;

      setError(null);
      setInput("");
      setSending(true);

      // Optimistic user message
      const tempId = `temp-${Date.now()}`;
      const thinkingId = `thinking-${Date.now()}`;
      setMessages((prev) => [
        ...prev,
        { id: tempId, role: "user", content: trimmed },
        { id: thinkingId, role: "assistant", content: "", thinking: true },
      ]);
      scrollToBottom();

      try {
        const res = await fetch(`${API_BASE}/copilot/chat`, {
          method: "POST",
          headers: buildApiHeaders(token, { "Content-Type": "application/json" }),
          body: JSON.stringify({ message: trimmed }),
        });

        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          throw new Error(err.detail || "AI 回應失敗");
        }

        const data = await res.json();
        const reply: string = data.reply || "（無回應）";

        setMessages((prev) => {
          // Replace thinking bubble with real reply
          const withoutThinking = prev.filter((m) => m.id !== thinkingId);
          return [
            ...withoutThinking,
            {
              id: `reply-${Date.now()}`,
              role: "assistant",
              content: reply,
              created_at: new Date().toISOString(),
            },
          ];
        });
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : "發生錯誤，請稍後再試";
        setError(msg);
        setMessages((prev) => prev.filter((m) => m.id !== thinkingId));
      } finally {
        setSending(false);
        setTimeout(() => textareaRef.current?.focus(), 50);
      }
    },
    [token, sending, scrollToBottom]
  );

  // ── Keyboard submit ───────────────────────────────────────────────────────
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send(input);
    }
  };

  // ── Clear history ─────────────────────────────────────────────────────────
  const clearHistory = async () => {
    if (!clearConfirm) {
      setClearConfirm(true);
      setTimeout(() => setClearConfirm(false), 3000);
      return;
    }
    setClearConfirm(false);
    try {
      await fetch(`${API_BASE}/copilot/chat/history`, {
        method: "DELETE",
        headers: buildApiHeaders(token),
      });
      setMessages([]);
    } catch {
      setError("清除失敗");
    }
  };

  // ── Render ────────────────────────────────────────────────────────────────
  const isEmpty = messages.length === 0 && !loadingHistory;

  return (
    <TooltipProvider>
      <div className="flex h-[calc(100vh-4rem)] flex-col">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-border/50 px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/15">
              <Bot className="h-5 w-5 text-primary" />
            </div>
            <div>
              <h1 className="text-base font-semibold leading-none">AI 行銷專員</h1>
              <p className="mt-0.5 text-xs text-muted-foreground">
                B2B 銷售智慧助理 · 即時 CRM 資料存取
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8 text-muted-foreground hover:text-foreground"
                  onClick={loadHistory}
                  disabled={loadingHistory}
                >
                  <RefreshCw className={cn("h-4 w-4", loadingHistory && "animate-spin")} />
                </Button>
              </TooltipTrigger>
              <TooltipContent>重新載入對話</TooltipContent>
            </Tooltip>

            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className={cn(
                    "h-8 w-8",
                    clearConfirm
                      ? "text-destructive hover:text-destructive"
                      : "text-muted-foreground hover:text-foreground"
                  )}
                  onClick={clearHistory}
                  disabled={messages.length === 0}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>
                {clearConfirm ? "再按一次確認清除" : "清除對話記錄"}
              </TooltipContent>
            </Tooltip>
          </div>
        </div>

        {/* Message list */}
        <div
          ref={scrollRef}
          className="flex-1 overflow-y-auto px-4 py-4 md:px-6"
        >
          {loadingHistory ? (
            <div className="flex h-full items-center justify-center">
              <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
            </div>
          ) : isEmpty ? (
            <div className="flex h-full flex-col items-center justify-center gap-6 text-center">
              <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10">
                <Sparkles className="h-8 w-8 text-primary" />
              </div>
              <div>
                <h2 className="text-lg font-semibold">你好，我是 AI 行銷專員</h2>
                <p className="mt-1 max-w-xs text-sm text-muted-foreground">
                  我能即時查詢你的 RFQ、訪客、聯絡人與漏斗數據，提供可行動的業務建議。
                </p>
              </div>
              <div className="flex flex-wrap justify-center gap-2">
                {SUGGESTIONS.map((s) => (
                  <button
                    key={s}
                    className="rounded-full border border-border/60 bg-card px-4 py-1.5 text-xs text-muted-foreground transition-colors hover:border-primary/40 hover:bg-primary/5 hover:text-foreground"
                    onClick={() => {
                      setInput(s);
                      textareaRef.current?.focus();
                    }}
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="mx-auto max-w-3xl space-y-4">
              {messages.map((msg) => (
                <MessageBubble key={msg.id} message={msg} />
              ))}
            </div>
          )}
        </div>

        {/* Error banner */}
        {error && (
          <div className="px-4 pb-2 md:px-6">
            <Alert variant="destructive" className="py-2">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription className="text-xs">{error}</AlertDescription>
            </Alert>
          </div>
        )}

        {/* Input area */}
        <div className="border-t border-border/50 px-4 py-4 md:px-6">
          <div className="mx-auto max-w-3xl">
            <div className="relative flex items-end gap-2 rounded-xl border border-border/60 bg-card px-4 py-3 shadow-sm focus-within:border-primary/50 focus-within:ring-1 focus-within:ring-primary/20 transition-all">
              <Textarea
                ref={textareaRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="輸入訊息… (Enter 傳送，Shift+Enter 換行)"
                className="min-h-[40px] max-h-40 flex-1 resize-none border-0 bg-transparent p-0 text-sm shadow-none focus-visible:ring-0 focus-visible:ring-offset-0 placeholder:text-muted-foreground/50"
                rows={1}
                disabled={sending}
              />
              <Button
                size="icon"
                className="h-8 w-8 shrink-0 rounded-lg"
                onClick={() => send(input)}
                disabled={!input.trim() || sending}
              >
                {sending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Send className="h-4 w-4" />
                )}
              </Button>
            </div>
            <p className="mt-1.5 text-center text-[10px] text-muted-foreground/40">
              AI 助理可能產生錯誤，重要決策請自行確認資料
            </p>
          </div>
        </div>
      </div>
    </TooltipProvider>
  );
}

// ── Message Bubble ─────────────────────────────────────────────────────────

function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === "user";

  return (
    <div className={cn("flex gap-3", isUser && "flex-row-reverse")}>
      {/* Avatar */}
      <div
        className={cn(
          "flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs",
          isUser
            ? "bg-primary/20 text-primary"
            : "bg-muted text-muted-foreground"
        )}
      >
        {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
      </div>

      {/* Bubble */}
      <div
        className={cn(
          "group relative max-w-[80%] rounded-2xl px-4 py-3 text-sm",
          isUser
            ? "rounded-tr-sm bg-primary text-primary-foreground"
            : "rounded-tl-sm bg-muted/60"
        )}
      >
        {message.thinking ? (
          <ThinkingDots />
        ) : isUser ? (
          <p className="whitespace-pre-wrap leading-relaxed">{message.content}</p>
        ) : (
          <div className="prose-sm max-w-none text-foreground">
            {renderContent(message.content)}
          </div>
        )}

        {message.created_at && !message.thinking && (
          <span className="mt-1 block text-right text-[10px] opacity-40">
            {formatTime(message.created_at)}
          </span>
        )}
      </div>
    </div>
  );
}
