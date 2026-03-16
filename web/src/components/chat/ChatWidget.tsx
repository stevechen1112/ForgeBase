"use client";

import { useMemo, useState, useEffect } from "react";
import { MessageCircle, X } from "lucide-react";

import { ChatPanel } from "@/components/chat/ChatPanel";
import type { ChatMessageItem, ChatMessageSource } from "@/components/chat/ChatMessage";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";

type ContextEntityType = "product" | "faq" | "home" | "category" | "application";

interface ChatWidgetProps {
  contextPage: string;
  contextEntityType: ContextEntityType;
  contextEntityId?: string;
}

interface CreateSessionResponse {
  data: {
    chat_session_id: string;
    greeting: string;
    suggestions: string[];
  };
}

interface MessageResponse {
  data: {
    reply: string;
    sources: ChatMessageSource[];
    suggested_action: "none" | "rfq" | "contact";
    handoff_ready: boolean;
    handoff_prefill: Record<string, unknown>;
    needs_clarification?: boolean;
    clarifying_question?: string | null;
  };
}

interface HandoffResponse {
  data: {
    rfq_prefill_url: string;
  };
}

function getVisitorId(): string {
  const match = document.cookie.match(/(?:^|;\s*)fb_vid=([^;]*)/);
  if (match) return decodeURIComponent(match[1]);
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    const visitorId = crypto.randomUUID();
    document.cookie = `fb_vid=${visitorId}; path=/; SameSite=Lax`;
    return visitorId;
  }
  const fallback = `fb-${Date.now()}`;
  document.cookie = `fb_vid=${fallback}; path=/; SameSite=Lax`;
  return fallback;
}

function getSessionId(): string {
  const key = "fb_sid";
  const existing = window.sessionStorage.getItem(key);
  if (existing) return existing;
  const sessionId = typeof crypto !== "undefined" && crypto.randomUUID ? crypto.randomUUID() : `fs-${Date.now()}`;
  window.sessionStorage.setItem(key, sessionId);
  return sessionId;
}

function getApiBase(): string {
  const raw = process.env.NEXT_PUBLIC_API_URL || "";
  const trimmed = raw.replace(/\/$/, "");
  if (trimmed.endsWith("/api/v1")) {
    return trimmed.slice(0, -7);
  }
  if (trimmed) return trimmed;
  if (typeof window === "undefined") return "";
  return window.location.origin;
}

export function ChatWidget({ contextPage, contextEntityType, contextEntityId }: ChatWidgetProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [isBusy, setIsBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [chatSessionId, setChatSessionId] = useState<string | null>(null);
  const [handoffUrl, setHandoffUrl] = useState<string | null>(null);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [messages, setMessages] = useState<ChatMessageItem[]>([]);
  const [isDesktop, setIsDesktop] = useState(true);

  useEffect(() => {
    const m = window.matchMedia("(min-width: 640px)");
    setIsDesktop(m.matches);
    const listener = (e: MediaQueryListEvent) => setIsDesktop(e.matches);
    m.addEventListener("change", listener);
    return () => m.removeEventListener("change", listener);
  }, []);

  const apiBase = useMemo(() => getApiBase(), []);

  async function ensureSession() {
    if (chatSessionId) return chatSessionId;

    setIsBusy(true);
    setError(null);
    try {
      const response = await fetch(`${apiBase}/api/v1/chat/sessions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          visitor_id: getVisitorId(),
          session_id: getSessionId(),
          context_page: contextPage,
          context_entity_type: contextEntityType,
          context_entity_id: contextEntityId,
          locale: document.documentElement.lang || "en",
        }),
      });

      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const payload = (await response.json()) as CreateSessionResponse;
      setChatSessionId(payload.data.chat_session_id);
      setSuggestions(payload.data.suggestions);
      setMessages([
        {
          id: `${payload.data.chat_session_id}-greeting`,
          role: "assistant",
          content: payload.data.greeting,
        },
      ]);
      return payload.data.chat_session_id;
    } catch {
      setError("The advisor is temporarily unavailable. Please try again shortly.");
      return null;
    } finally {
      setIsBusy(false);
    }
  }

  async function openWidget(nextOpen: boolean) {
    setIsOpen(nextOpen);
    if (nextOpen && !chatSessionId) {
      await ensureSession();
    }
  }

  async function handleSubmit(content: string) {
    const sessionId = await ensureSession();
    if (!sessionId) return;

    setIsBusy(true);
    setError(null);
    setMessages((current) => [
      ...current,
      { id: `${Date.now()}-user`, role: "user", content },
    ]);

    try {
      const response = await fetch(`${apiBase}/api/v1/chat/sessions/${sessionId}/messages`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          visitor_id: getVisitorId(),
          content,
          locale: document.documentElement.lang || "en",
        }),
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      const payload = (await response.json()) as MessageResponse;
      setMessages((current) => [
        ...current,
        {
          id: `${Date.now()}-assistant`,
          role: "assistant",
          content: payload.data.reply,
          sources: payload.data.sources,
        },
      ]);

      if (payload.data.handoff_ready || payload.data.suggested_action === "rfq") {
        const handoffResponse = await fetch(`${apiBase}/api/v1/chat/sessions/${sessionId}/handoff`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            visitor_id: getVisitorId(),
            intent_reason: "chat_handoff_ready",
            prefill: payload.data.handoff_prefill,
          }),
        });
        if (handoffResponse.ok) {
          const handoffPayload = (await handoffResponse.json()) as HandoffResponse;
          setHandoffUrl(handoffPayload.data.rfq_prefill_url);
        }
      }
    } catch {
      setError("The advisor could not complete that request. Please try again or continue with RFQ.");
    } finally {
      setIsBusy(false);
    }
  }

  return (
    <>
      <div className="fixed bottom-5 right-5 z-50 hidden sm:block">
        {isOpen && isDesktop ? (
          <div className="flex flex-col h-[min(560px,calc(100vh-96px))] w-[min(360px,calc(100vw-32px))] lg:w-[380px]">
            <div className="mb-2 flex justify-end shrink-0">
              <Button variant="secondary" size="icon" className="h-8 w-8 rounded-full shadow-md" onClick={() => void openWidget(false)}>
                <X className="h-4 w-4" />
              </Button>
            </div>
            <div className="flex-1 min-h-0">
              <ChatPanel
                messages={messages}
                suggestions={suggestions}
                isBusy={isBusy}
                error={error}
                handoffUrl={handoffUrl}
                onSuggestionClick={handleSubmit}
                onSubmit={handleSubmit}
              />
            </div>
          </div>
        ) : (
          <Button className="h-14 rounded-full px-5 shadow-xl" onClick={() => void openWidget(true)}>
            <MessageCircle className="mr-1 h-5 w-5" />
            Ask Product Advisor
          </Button>
        )}
      </div>

      <div className="fixed bottom-4 right-4 z-50 sm:hidden">
        <Sheet open={isOpen && !isDesktop} onOpenChange={(open) => void openWidget(open)}>
          {!isOpen && (
            <Button className="h-14 rounded-full px-5 shadow-xl" onClick={() => void openWidget(true)}>
              <MessageCircle className="mr-1 h-5 w-5" />
              Ask Advisor
            </Button>
          )}
          <SheetContent side="bottom" className="h-[78vh] max-h-[720px] rounded-t-2xl p-0 sm:max-w-none">
            <SheetHeader className="border-b border-slate-200 px-4 py-3">
              <SheetTitle>AI Product Advisor</SheetTitle>
            </SheetHeader>
            <div className="h-[calc(78vh-57px)] max-h-[663px]">
              <ChatPanel
                messages={messages}
                suggestions={suggestions}
                isBusy={isBusy}
                error={error}
                handoffUrl={handoffUrl}
                onSuggestionClick={handleSubmit}
                onSubmit={handleSubmit}
              />
            </div>
          </SheetContent>
        </Sheet>
      </div>
    </>
  );
}