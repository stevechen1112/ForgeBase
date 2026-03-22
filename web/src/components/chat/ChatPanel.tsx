"use client";

import Link from "next/link";
import { MessageSquareText } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ChatInput } from "@/components/chat/ChatInput";
import { ChatMessage, type ChatMessageItem } from "@/components/chat/ChatMessage";
import { useMessageNamespace } from "@/lib/messages";

type ChatMessages = {
  title: string;
  subtitle: string;
  suggestedQuestions: string;
  rfqReady: string;
  rfqReadyDescription: string;
  prepareRfq: string;
  thinking: string;
};

interface ChatPanelProps {
  title?: string;
  subtitle?: string;
  messages: ChatMessageItem[];
  suggestions: string[];
  isBusy: boolean;
  error: string | null;
  handoffUrl: string | null;
  onSuggestionClick: (value: string) => Promise<void>;
  onSubmit: (value: string) => Promise<void>;
}

export function ChatPanel({
  title,
  subtitle,
  messages,
  suggestions,
  isBusy,
  error,
  handoffUrl,
  onSuggestionClick,
  onSubmit,
}: ChatPanelProps) {
  const copy = useMessageNamespace<ChatMessages>("chat");
  const resolvedTitle = title ?? copy.title;
  const resolvedSubtitle = subtitle ?? copy.subtitle;

  return (
    <Card className="flex h-full flex-col overflow-hidden border-slate-200 shadow-xl">
      <CardHeader className="border-b border-slate-200 bg-slate-950 px-4 py-4 text-white">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-white/10">
            <MessageSquareText className="h-5 w-5" />
          </div>
          <div>
            <CardTitle className="text-base text-white">{resolvedTitle}</CardTitle>
            <p className="mt-1 text-xs text-slate-300">{resolvedSubtitle}</p>
          </div>
        </div>
      </CardHeader>

      <CardContent className="flex min-h-0 flex-1 flex-col bg-slate-50 p-0">
        <div className="flex-1 space-y-4 overflow-y-auto px-4 py-4">
          {messages.map((message) => (
            <ChatMessage key={message.id} message={message} />
          ))}

          {messages.length <= 1 && suggestions.length > 0 && (
            <div className="space-y-2">
              <p className="text-xs font-medium uppercase tracking-[0.16em] text-slate-400">
                {copy.suggestedQuestions}
              </p>
              <div className="flex flex-wrap gap-2">
                {suggestions.map((suggestion) => (
                  <button
                    key={suggestion}
                    type="button"
                    className="rounded-full border border-slate-200 bg-white px-3 py-2 text-left text-xs text-slate-600 transition hover:border-slate-300 hover:text-slate-900"
                    onClick={() => void onSuggestionClick(suggestion)}
                    disabled={isBusy}
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            </div>
          )}

          {handoffUrl && (
            <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4">
              <Badge variant="success" className="mb-2">{copy.rfqReady}</Badge>
              <p className="text-sm text-emerald-800">
                {copy.rfqReadyDescription}
              </p>
              <Button asChild className="mt-3">
                <Link href={handoffUrl}>{copy.prepareRfq}</Link>
              </Button>
            </div>
          )}

          {isBusy && (
            <div className="text-sm text-slate-500">{copy.thinking}</div>
          )}

          {error && (
            <div className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-700">
              {error}
            </div>
          )}
        </div>

        <ChatInput disabled={isBusy} onSubmit={onSubmit} />
      </CardContent>
    </Card>
  );
}