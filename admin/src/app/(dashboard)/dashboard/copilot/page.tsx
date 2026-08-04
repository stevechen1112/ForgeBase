"use client";
import { useEffect, useRef, useState, useCallback } from "react";
import { useAuth } from "@/lib/auth/store";
import { API_BASE, buildApiHeaders } from "@/lib/api/client";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import {
  Bot, Send, Trash2, Loader2, RefreshCw,
  User, AlertCircle, Zap, ShieldAlert, Clock, BarChart2,
} from "lucide-react";

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

function inlineRender(text: string): React.ReactNode {
  const parts = text.split(/(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)/g);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**"))
      return <strong key={i}>{part.slice(2, -2)}</strong>;
    if (part.startsWith("*") && part.endsWith("*"))
      return <em key={i}>{part.slice(1, -1)}</em>;
    if (part.startsWith("`") && part.endsWith("`"))
      return <code key={i} className="rounded bg-muted px-1 py-0.5 text-[11px] font-mono">{part.slice(1, -1)}</code>;
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
      nodes.push(<pre key={nodeKey++} className="my-1.5 rounded bg-muted p-2 text-[11px] font-mono overflow-x-auto"><code>{codeLines.join("\n")}</code></pre>);
    } else if (/^[-•*]\s/.test(line.trim())) {
      const items: string[] = [];
      while (i < lines.length && /^[-•*]\s/.test(lines[i].trim())) {
        items.push(lines[i].replace(/^[-•*]\s/, "").trim()); i++;
      }
      nodes.push(<ul key={nodeKey++} className="my-1 ml-3 list-disc space-y-0.5 text-sm">{items.map((it, k) => <li key={k}>{inlineRender(it)}</li>)}</ul>);
      continue;
    } else if (/^#{1,3}\s/.test(line)) {
      nodes.push(<p key={nodeKey++} className="mt-2 mb-0.5 text-sm font-semibold">{inlineRender(line.replace(/^#{1,3}\s/, ""))}</p>);
    } else if (/^---+$/.test(line.trim())) {
      nodes.push(<hr key={nodeKey++} className="my-1.5" />);
    } else if (line.trim() === "") {
      nodes.push(<div key={nodeKey++} className="h-1" />);
    } else {
      nodes.push(<p key={nodeKey++} className="text-sm leading-relaxed">{inlineRender(line)}</p>);
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

const QUICK_PROMPTS = [
  "今天有幾個新 RFQ？",
  "有 RFQ 超期未回覆嗎？",
  "目前有哪些高關注訪客？",
  "最近成交了哪些客戶？",
  "漏斗轉換率是多少？",
];

export default function CopilotPage() {
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";

  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [clearConfirm, setClearConfirm] = useState(false);
  const [stats, setStats] = useState<CopilotStats | null>(null);

  const scrollRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const scrollToBottom = useCallback(() => {
    requestAnimationFrame(() => {
      if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    });
  }, []);

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

  useEffect(() => { loadHistory(); loadStats(); }, [loadHistory, loadStats]);
  useEffect(() => { scrollToBottom(); }, [messages, scrollToBottom]);

  const send = useCallback(async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || sending) return;
    setError(null); setInput(""); setSending(true);
    const tempId = `temp-${Date.now()}`;
    const thinkId = `think-${Date.now()}`;
    setMessages(prev => [
      ...prev,
      { id: tempId, role: "user", content: trimmed },
      { id: thinkId, role: "assistant", content: "", thinking: true },
    ]);
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
        return [...filtered, { id: `r-${Date.now()}`, role: "assistant" as const, content: reply || "（無回應）", created_at: new Date().toISOString() }];
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "發生錯誤");
      setMessages(prev => prev.filter(m => m.id !== thinkId));
    } finally {
      setSending(false);
      setTimeout(() => textareaRef.current?.focus(), 50);
    }
  }, [token, sending, scrollToBottom]);

  const clearHistory = async () => {
    if (!clearConfirm) { setClearConfirm(true); setTimeout(() => setClearConfirm(false), 3000); return; }
    setClearConfirm(false);
    try {
      await fetch(`${API_BASE}/copilot/chat/history`, { method: "DELETE", headers: buildApiHeaders(token) });
      setMessages([]);
    } catch { setError("清除失敗"); }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(input); }
  };

  return (
    <div className="flex h-[calc(100vh-5rem)] gap-6">

      {/* ─── 主聊天區 ─── */}
      <div className="flex flex-1 flex-col overflow-hidden rounded-xl border bg-card shadow-sm">
        {/* Header */}
        <div className="flex shrink-0 items-center gap-3 border-b px-5 py-4">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary/10">
            <Bot className="h-5 w-5 text-primary" />
          </div>
          <div className="flex-1">
            <h1 className="text-base font-semibold leading-tight">AI 行銷助理</h1>
            <p className="text-xs text-muted-foreground">以對話方式查詢詢價、訪客與成交進度</p>
          </div>
          <div className="flex items-center gap-1.5">
            <Button variant="ghost" size="sm" className="gap-1.5 text-xs text-muted-foreground" onClick={() => { loadHistory(); loadStats(); }} disabled={loadingHistory}>
              <RefreshCw className={cn("h-3.5 w-3.5", loadingHistory && "animate-spin")} />
              重新整理
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className={cn("gap-1.5 text-xs", clearConfirm ? "text-destructive" : "text-muted-foreground")}
              onClick={clearHistory}
              disabled={messages.length === 0}
            >
              <Trash2 className="h-3.5 w-3.5" />
              {clearConfirm ? "確認清除" : "清除記錄"}
            </Button>
          </div>
        </div>

        {/* Stats bar */}
        {stats && stats.total_runs > 0 && (
          <div className="flex shrink-0 flex-wrap items-center gap-x-4 gap-y-1 border-b bg-muted/30 px-5 py-2">
            <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <BarChart2 className="h-3.5 w-3.5 text-primary/50" />
              7天 <strong className="text-foreground">{stats.total_runs}</strong> 次對話
            </span>
            <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <Zap className="h-3.5 w-3.5 text-amber-500/70" />
              工具命中率 <strong className={cn(stats.tool_hit_rate >= 60 ? "text-amber-500" : "text-foreground")}>{stats.tool_hit_rate}%</strong>
            </span>
            <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <ShieldAlert className={cn("h-3.5 w-3.5", stats.error_rate > 5 ? "text-destructive" : "text-muted-foreground/50")} />
              錯誤率 <strong className={cn(stats.error_rate > 5 ? "text-destructive" : "text-foreground")}>{stats.error_rate}%</strong>
            </span>
            <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <Clock className="h-3.5 w-3.5 text-muted-foreground/50" />
              平均 <strong className={cn(stats.avg_duration_ms > 8000 ? "text-amber-500" : "text-foreground")}>{(stats.avg_duration_ms / 1000).toFixed(1)}s</strong>
            </span>
            {stats.top_tools.length > 0 && (
              <span className="text-xs text-muted-foreground">
                常用工具：{stats.top_tools.slice(0, 3).map(t => t.name).join("、")}
              </span>
            )}
          </div>
        )}

        {/* Messages */}
        <div ref={scrollRef} className="flex-1 overflow-y-auto px-5 py-4 space-y-4">
          {loadingHistory ? (
            <div className="flex h-full items-center justify-center">
              <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
            </div>
          ) : messages.length === 0 ? (
            <div className="flex h-full flex-col items-center justify-center gap-4 text-center px-6">
              <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/10">
                <Bot className="h-7 w-7 text-primary" />
              </div>
              <div>
                <p className="text-sm font-medium">詢問任何業務問題</p>
                <p className="mt-1 text-xs text-muted-foreground">可查詢詢價、訪客關注度與漏斗數據，並提供可執行建議。</p>
              </div>
            </div>
          ) : (
            messages.map(msg => {
              const isUser = msg.role === "user";
              return (
                <div key={msg.id} className={cn("flex gap-3", isUser && "flex-row-reverse")}>
                  <div className={cn(
                    "flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs",
                    isUser ? "bg-primary/15 text-primary" : "bg-muted text-muted-foreground"
                  )}>
                    {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
                  </div>
                  <div className={cn(
                    "max-w-[78%] rounded-2xl px-4 py-2.5",
                    isUser
                      ? "rounded-tr-sm bg-primary text-primary-foreground"
                      : "rounded-tl-sm bg-muted/60"
                  )}>
                    {msg.thinking ? <ThinkingDots /> : isUser
                      ? <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.content}</p>
                      : <div className="text-foreground">{renderContent(msg.content)}</div>
                    }
                    {msg.created_at && !msg.thinking && (
                      <span className="mt-0.5 block text-right text-[10px] opacity-40">
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
          <div className="px-5 pb-2">
            <Alert variant="destructive" className="py-2">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription className="text-sm">{error}</AlertDescription>
            </Alert>
          </div>
        )}

        {/* Input */}
        <div className="shrink-0 border-t px-4 py-3">
          <div className="flex items-end gap-2 rounded-xl border bg-background px-3 py-2 focus-within:ring-1 focus-within:ring-ring">
            <Textarea
              ref={textareaRef}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="輸入問題，按 Enter 發送（Shift+Enter 換行）"
              rows={1}
              className="flex-1 resize-none border-0 bg-transparent p-0 text-sm shadow-none focus-visible:ring-0 focus-visible:ring-offset-0"
              style={{ minHeight: "24px", maxHeight: "120px" }}
              disabled={sending}
            />
            <Button
              size="sm"
              className="h-8 w-8 shrink-0 rounded-lg p-0"
              onClick={() => send(input)}
              disabled={!input.trim() || sending}
            >
              {sending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
            </Button>
          </div>
        </div>
      </div>

      {/* ─── 右側欄 ─── */}
      <div className="hidden w-64 flex-col gap-4 xl:flex">
        {/* 快速提問 */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm">快速提問</CardTitle>
          </CardHeader>
          <CardContent className="space-y-1.5">
            {QUICK_PROMPTS.map(p => (
              <button
                key={p}
                onClick={() => { setInput(p); textareaRef.current?.focus(); }}
                className="w-full rounded-lg border border-border/60 bg-muted/30 px-3 py-2 text-left text-xs text-muted-foreground hover:border-primary/40 hover:bg-primary/5 hover:text-foreground transition-colors"
              >
                {p}
              </button>
            ))}
          </CardContent>
        </Card>

        {/* Copilot 說明 */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm">可查詢的資料</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {[
              { label: "RFQ 詢價單", desc: "狀態、逾時、優先級" },
              { label: "買家關注度", desc: "高度關注／可成交名單" },
              { label: "轉換漏斗", desc: "各階段數量與比率" },
              { label: "聯絡人", desc: "歷史 RFQ、行為紀錄" },
              { label: "產品熱度", desc: "近期詢問最多的產品" },
            ].map(({ label, desc }) => (
              <div key={label} className="flex flex-col">
                <span className="text-xs font-medium text-foreground">{label}</span>
                <span className="text-[11px] text-muted-foreground">{desc}</span>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
