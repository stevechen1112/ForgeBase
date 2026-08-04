"use client";
import { useEffect, useRef, useState, useCallback } from "react";
import { useAuth } from "@/lib/auth/store";
import { API_BASE, buildApiHeaders } from "@/lib/api/client";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import {
  Bot, Send, Trash2, Loader2, RefreshCw, X, Minus,
  User, AlertCircle, Zap, ShieldAlert, Clock, BarChart2,
} from "lucide-react";

// ── Types ─────────────────────────────────────────────────────────────────────

type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
  created_at?: string;
  pending?: boolean;
  thinking?: boolean;
};

type CopilotStats = {
  period: string;
  total_runs: number;
  tool_hit_rate: number;
  error_rate: number;
  avg_duration_ms: number;
  top_tools: { name: string; count: number }[];
};

// ── Inline markdown renderer ──────────────────────────────────────────────────

function inlineRender(text: string): React.ReactNode {
  const parts = text.split(/(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)/g);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**"))
      return <strong key={i}>{part.slice(2, -2)}</strong>;
    if (part.startsWith("*") && part.endsWith("*"))
      return <em key={i}>{part.slice(1, -1)}</em>;
    if (part.startsWith("`") && part.endsWith("`"))
      return <code key={i} className="rounded bg-black/30 px-1 py-0.5 text-[11px] font-mono">{part.slice(1, -1)}</code>;
    return part;
  });
}

function renderContent(text: string): React.ReactNode {
  const lines = text.split("\n");
  const nodes: React.ReactNode[] = [];
  let i = 0;
  let nodeKey = 0;

  while (i < lines.length) {
    const line = lines[i];
    if (line.startsWith("```")) {
      const codeLines: string[] = [];
      i++;
      while (i < lines.length && !lines[i].startsWith("```")) { codeLines.push(lines[i]); i++; }
      nodes.push(<pre key={nodeKey++} className="my-1.5 rounded bg-black/30 p-2 text-[11px] font-mono overflow-x-auto"><code>{codeLines.join("\n")}</code></pre>);
    } else if (/^[-•*]\s/.test(line.trim())) {
      const items: string[] = [];
      while (i < lines.length && /^[-•*]\s/.test(lines[i].trim())) {
        items.push(lines[i].replace(/^[-•*]\s/, "").trim()); i++;
      }
      nodes.push(<ul key={nodeKey++} className="my-1 ml-3 list-disc space-y-0.5 text-xs">{items.map((it, k) => <li key={k}>{inlineRender(it)}</li>)}</ul>);
      continue;
    } else if (/^#{1,3}\s/.test(line)) {
      nodes.push(<p key={nodeKey++} className="mt-2 mb-0.5 text-xs font-semibold">{inlineRender(line.replace(/^#{1,3}\s/, ""))}</p>);
    } else if (/^---+$/.test(line.trim())) {
      nodes.push(<hr key={nodeKey++} className="my-1.5 border-white/10" />);
    } else if (line.trim() === "") {
      nodes.push(<div key={nodeKey++} className="h-1" />);
    } else {
      nodes.push(<p key={nodeKey++} className="text-xs leading-relaxed">{inlineRender(line)}</p>);
    }
    i++;
  }
  return <>{nodes}</>;
}

function ThinkingDots() {
  return (
    <span className="flex items-center gap-1 py-0.5">
      {[0, 1, 2].map((i) => (
        <span key={i} className="h-1.5 w-1.5 rounded-full bg-current opacity-70"
          style={{ animation: "bounce 1.2s infinite ease-in-out both", animationDelay: `${i * 0.2}s` }} />
      ))}
      <style>{`@keyframes bounce{0%,80%,100%{transform:translateY(0);opacity:.4}40%{transform:translateY(-4px);opacity:1}}`}</style>
    </span>
  );
}

// ── Floating Widget ───────────────────────────────────────────────────────────

export function CopilotFloatingWidget() {
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";

  const [open, setOpen] = useState(false);
  const [minimised, setMinimised] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [clearConfirm, setClearConfirm] = useState(false);
  const [stats, setStats] = useState<CopilotStats | null>(null);
  const [unread, setUnread] = useState(0);

  const scrollRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const scrollToBottom = useCallback(() => {
    requestAnimationFrame(() => {
      if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    });
  }, []);

  // Load history when first opened
  const loadHistory = useCallback(async () => {
    if (!token) return;
    setLoadingHistory(true);
    try {
      const res = await fetch(`${API_BASE}/copilot/chat/history?limit=40`, { headers: buildApiHeaders(token) });
      if (!res.ok) throw new Error();
      const data = await res.json();
      setMessages(data.data || []);
    } catch { /* start fresh */ }
    finally { setLoadingHistory(false); }
  }, [token]);

  const loadStats = useCallback(async () => {
    if (!token) return;
    try {
      const res = await fetch(`${API_BASE}/copilot/stats`, { headers: buildApiHeaders(token) });
      if (res.ok) setStats(await res.json());
    } catch { /* non-critical */ }
  }, [token]);

  useEffect(() => {
    if (open && messages.length === 0) { loadHistory(); loadStats(); }
    if (open) { setUnread(0); setTimeout(() => textareaRef.current?.focus(), 100); }
  }, [open, messages.length, loadHistory, loadStats]);

  useEffect(() => { scrollToBottom(); }, [messages, scrollToBottom]);

  // Send message
  const send = useCallback(async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || sending) return;
    setError(null); setInput(""); setSending(true);

    const tempId = `temp-${Date.now()}`;
    const thinkId = `think-${Date.now()}`;
    setMessages(prev => [...prev, { id: tempId, role: "user", content: trimmed }, { id: thinkId, role: "assistant", content: "", thinking: true }]);
    scrollToBottom();

    try {
      const res = await fetch(`${API_BASE}/copilot/chat`, {
        method: "POST",
        headers: buildApiHeaders(token, { "Content-Type": "application/json" }),
        body: JSON.stringify({ message: trimmed }),
      });
      if (!res.ok) { const e = await res.json().catch(() => ({})); throw new Error(e.detail || "AI 回應失敗"); }
      const { reply } = await res.json();

      setMessages(prev => {
        const filtered = prev.filter(m => m.id !== thinkId);
        return [...filtered, { id: `r-${Date.now()}`, role: "assistant", content: reply || "（無回應）", created_at: new Date().toISOString() }];
      });
      if (!open) setUnread(n => n + 1);
    } catch (err) {
      setError(err instanceof Error ? err.message : "發生錯誤");
      setMessages(prev => prev.filter(m => m.id !== thinkId));
    } finally {
      setSending(false);
      setTimeout(() => textareaRef.current?.focus(), 50);
    }
  }, [token, sending, open, scrollToBottom]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(input); }
  };

  const clearHistory = async () => {
    if (!clearConfirm) { setClearConfirm(true); setTimeout(() => setClearConfirm(false), 3000); return; }
    setClearConfirm(false);
    try {
      await fetch(`${API_BASE}/copilot/chat/history`, { method: "DELETE", headers: buildApiHeaders(token) });
      setMessages([]);
    } catch { setError("清除失敗"); }
  };

  // Only render for authenticated users
  if (state.status !== "authenticated") return null;

  return (
    <TooltipProvider>
      {/* ── Floating Button ── */}
      <div className="fixed bottom-6 right-6 z-50 flex flex-col items-end gap-3">

        {/* ── Chat Panel ── */}
        {open && (
          <div
            className={cn(
              "flex flex-col rounded-2xl border border-border/60 bg-background shadow-2xl shadow-black/30 transition-all duration-200",
              minimised ? "h-14 w-72 overflow-hidden" : "h-[560px] w-[380px]"
            )}
            style={{ maxHeight: "calc(100vh - 100px)" }}
          >
            {/* Panel header */}
            <div className="flex shrink-0 items-center gap-2.5 border-b border-border/50 px-4 py-3">
              <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary/15">
                <Bot className="h-4 w-4 text-primary" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold leading-none">AI 行銷助理</p>
                <p className="mt-0.5 text-[10px] text-muted-foreground truncate">即時 CRM 資料存取</p>
              </div>
              <div className="flex items-center gap-1">
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button variant="ghost" size="icon" className="h-6 w-6 text-muted-foreground hover:text-foreground"
                      onClick={() => { loadHistory(); loadStats(); }}>
                      <RefreshCw className={cn("h-3.5 w-3.5", loadingHistory && "animate-spin")} />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent side="left">重新載入</TooltipContent>
                </Tooltip>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button variant="ghost" size="icon"
                      className={cn("h-6 w-6", clearConfirm ? "text-destructive hover:text-destructive" : "text-muted-foreground hover:text-foreground")}
                      onClick={clearHistory} disabled={messages.length === 0}>
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent side="left">{clearConfirm ? "再按一次確認清除" : "清除記錄"}</TooltipContent>
                </Tooltip>
                <Button variant="ghost" size="icon" className="h-6 w-6 text-muted-foreground hover:text-foreground"
                  onClick={() => setMinimised(m => !m)}>
                  <Minus className="h-3.5 w-3.5" />
                </Button>
                <Button variant="ghost" size="icon" className="h-6 w-6 text-muted-foreground hover:text-foreground"
                  onClick={() => setOpen(false)}>
                  <X className="h-3.5 w-3.5" />
                </Button>
              </div>
            </div>

            {!minimised && (
              <>
                {/* Stats bar */}
                {stats && stats.total_runs > 0 && (
                  <div className="flex shrink-0 flex-wrap items-center gap-x-3 gap-y-1 border-b border-border/40 bg-muted/30 px-4 py-1.5">
                    <span className="flex items-center gap-1 text-[10px] text-muted-foreground">
                      <BarChart2 className="h-3 w-3 text-primary/50" />
                      <span>7天 <strong className="text-foreground">{stats.total_runs}</strong> 次</span>
                    </span>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <span className="flex items-center gap-1 text-[10px] text-muted-foreground cursor-default">
                          <Zap className="h-3 w-3 text-amber-500/60" />
                          <span className={cn(stats.tool_hit_rate >= 60 ? "text-amber-500" : "text-foreground")}>{stats.tool_hit_rate}%</span>
                        </span>
                      </TooltipTrigger>
                      <TooltipContent side="bottom" className="text-xs">
                        工具命中率 · 前3：{stats.top_tools.slice(0,3).map(t=>t.name).join("、") || "—"}
                      </TooltipContent>
                    </Tooltip>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <span className="flex items-center gap-1 text-[10px] cursor-default">
                          <ShieldAlert className={cn("h-3 w-3", stats.error_rate > 5 ? "text-destructive" : "text-muted-foreground/40")} />
                          <span className={cn(stats.error_rate > 5 ? "text-destructive" : "text-muted-foreground")}>錯誤 {stats.error_rate}%</span>
                        </span>
                      </TooltipTrigger>
                      <TooltipContent side="bottom" className="text-xs">Fallback 回應比例（&gt;5% 需關注）</TooltipContent>
                    </Tooltip>
                    <span className="flex items-center gap-1 text-[10px] text-muted-foreground">
                      <Clock className="h-3 w-3 text-muted-foreground/40" />
                      <span className={cn(stats.avg_duration_ms > 8000 ? "text-amber-500" : "")}>{(stats.avg_duration_ms / 1000).toFixed(1)}s</span>
                    </span>
                  </div>
                )}

                {/* Messages */}
                <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
                  {loadingHistory ? (
                    <div className="flex h-full items-center justify-center">
                      <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                    </div>
                  ) : messages.length === 0 ? (
                    <div className="flex h-full flex-col items-center justify-center gap-3 text-center px-4">
                      <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10">
                        <Bot className="h-6 w-6 text-primary" />
                      </div>
                      <p className="text-xs text-muted-foreground leading-relaxed">我能即時查詢 RFQ、訪客、漏斗資料，提供可行動的業務建議。</p>
                      <div className="flex flex-wrap justify-center gap-1.5 mt-1">
                        {["今天有幾個新 RFQ？", "熱門訪客有哪些？", "有 RFQ 超期未回覆嗎？"].map(s => (
                          <button key={s}
                            className="rounded-full border border-border/60 bg-card px-3 py-1 text-[11px] text-muted-foreground hover:border-primary/40 hover:bg-primary/5 hover:text-foreground transition-colors"
                            onClick={() => { setInput(s); textareaRef.current?.focus(); }}>
                            {s}
                          </button>
                        ))}
                      </div>
                    </div>
                  ) : (
                    messages.map(msg => {
                      const isUser = msg.role === "user";
                      return (
                        <div key={msg.id} className={cn("flex gap-2", isUser && "flex-row-reverse")}>
                          <div className={cn("flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs",
                            isUser ? "bg-primary/20 text-primary" : "bg-muted text-muted-foreground")}>
                            {isUser ? <User className="h-3.5 w-3.5" /> : <Bot className="h-3.5 w-3.5" />}
                          </div>
                          <div className={cn("max-w-[82%] rounded-2xl px-3 py-2",
                            isUser ? "rounded-tr-sm bg-primary text-primary-foreground text-xs" : "rounded-tl-sm bg-muted/60")}>
                            {msg.thinking ? <ThinkingDots /> : isUser
                              ? <p className="text-xs leading-relaxed whitespace-pre-wrap">{msg.content}</p>
                              : <div className="prose-sm max-w-none text-foreground">{renderContent(msg.content)}</div>
                            }
                            {msg.created_at && !msg.thinking && (
                              <span className="mt-0.5 block text-right text-[9px] opacity-40">
                                {new Date(msg.created_at).toLocaleTimeString("zh-TW", { hour: "2-digit", minute: "2-digit" })}
                              </span>
                            )}
                          </div>
                        </div>
                      );
                    })
                  )}
                </div>

                {/* Error */}
                {error && (
                  <div className="px-4 pb-2">
                    <Alert variant="destructive" className="py-1.5">
                      <AlertCircle className="h-3.5 w-3.5" />
                      <AlertDescription className="text-xs">{error}</AlertDescription>
                    </Alert>
                  </div>
                )}

                {/* Input */}
                <div className="shrink-0 border-t border-border/50 px-3 py-3">
                  <div className="relative flex items-end gap-2 rounded-xl border border-border/60 bg-card px-3 py-2 shadow-sm focus-within:border-primary/50 focus-within:ring-1 focus-within:ring-primary/20 transition-all">
                    <Textarea
                      ref={textareaRef}
                      value={input}
                      onChange={e => setInput(e.target.value)}
                      onKeyDown={handleKeyDown}
                      placeholder="輸入訊息…（Enter 傳送）"
                      className="min-h-[32px] max-h-28 flex-1 resize-none border-0 bg-transparent p-0 text-xs shadow-none focus-visible:ring-0 focus-visible:ring-offset-0 placeholder:text-muted-foreground/50"
                      rows={1}
                      disabled={sending}
                    />
                    <Button size="icon" className="h-7 w-7 shrink-0 rounded-lg"
                      onClick={() => send(input)} disabled={!input.trim() || sending}>
                      {sending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Send className="h-3.5 w-3.5" />}
                    </Button>
                  </div>
                </div>
              </>
            )}
          </div>
        )}

        {/* Toggle button */}
        <Tooltip>
          <TooltipTrigger asChild>
            <button
              onClick={() => { setOpen(o => !o); setMinimised(false); }}
              className={cn(
                "relative flex h-14 w-14 items-center justify-center rounded-full shadow-lg shadow-black/30 transition-all duration-200",
                "bg-primary text-primary-foreground hover:scale-105 hover:shadow-xl hover:shadow-primary/30 active:scale-95",
                open && "rotate-12"
              )}
              aria-label="AI 行銷助理"
            >
              {open
                ? <X className="h-6 w-6 transition-transform duration-200" />
                : <Bot className="h-6 w-6 transition-transform duration-200" />
              }
              {!open && unread > 0 && (
                <span className="absolute -right-1 -top-1 flex h-5 w-5 items-center justify-center rounded-full bg-destructive text-[10px] font-bold text-white">
                  {unread > 9 ? "9+" : unread}
                </span>
              )}
            </button>
          </TooltipTrigger>
          <TooltipContent side="left">{open ? "關閉 AI 助理" : "AI 行銷助理"}</TooltipContent>
        </Tooltip>
      </div>
    </TooltipProvider>
  );
}
