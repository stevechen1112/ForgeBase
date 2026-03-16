"use client";

import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

export interface ChatMessageSource {
  type: string;
  id: string;
  name: string;
  url?: string | null;
}

export interface ChatMessageItem {
  id: string;
  role: "assistant" | "user";
  content: string;
  sources?: ChatMessageSource[];
}

interface ChatMessageProps {
  message: ChatMessageItem;
}

export function ChatMessage({ message }: ChatMessageProps) {
  const isAssistant = message.role === "assistant";

  return (
    <div className={cn("flex w-full", isAssistant ? "justify-start" : "justify-end")}>
      <div
        className={cn(
          "max-w-[88%] rounded-2xl px-4 py-3 text-sm leading-6 shadow-sm",
          isAssistant
            ? "bg-white text-slate-700 border border-slate-200"
            : "bg-slate-900 text-white"
        )}
      >
        <p className="whitespace-pre-wrap">{message.content}</p>
        {isAssistant && message.sources && message.sources.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-2">
            {message.sources.slice(0, 2).map((source) => (
              source.url ? (
                <a
                  key={`${source.type}-${source.id}`}
                  href={source.url}
                  className="inline-flex"
                >
                  <Badge variant="info" className="cursor-pointer hover:bg-blue-200">
                    {source.name}
                  </Badge>
                </a>
              ) : (
                <Badge key={`${source.type}-${source.id}`} variant="info">
                  {source.name}
                </Badge>
              )
            ))}
          </div>
        )}
      </div>
    </div>
  );
}