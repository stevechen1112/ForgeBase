"use client";

import { Badge } from "@/components/ui/badge";
import { getChatUiCopy } from "@/components/chat/chat-ui-copy";
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
  locale?: string;
  sources?: ChatMessageSource[];
  groundingStatus?: "grounded" | "limited" | "blocked";
  claimWarnings?: string[];
}

interface ChatMessageProps {
  message: ChatMessageItem;
}

export function ChatMessage({ message }: ChatMessageProps) {
  const isAssistant = message.role === "assistant";
  const responseCopy = getChatUiCopy(message.locale);
  const isZh = typeof document !== "undefined" && document.documentElement.lang.toLowerCase().startsWith("zh");
  const basePath = process.env.NEXT_PUBLIC_BASE_PATH || "";
  const sourceHref = (url: string) => {
    const localizedUrl = isZh && url.startsWith("/") && url !== "/zh-TW" && !url.startsWith("/zh-TW/")
      ? `/zh-TW${url}`
      : url;
    return localizedUrl.startsWith("/") && basePath && !localizedUrl.startsWith(`${basePath}/`)
      ? `${basePath}${localizedUrl}`
      : localizedUrl;
  };

  return (
    <div className={cn("flex w-full", isAssistant ? "justify-start" : "justify-end")}>
      <div
        dir="auto"
        className={cn(
          "max-w-[88%] rounded-2xl px-4 py-3 text-sm leading-6 shadow-sm",
          isAssistant
            ? "bg-white text-slate-700 border border-slate-200"
            : "bg-slate-900 text-white"
        )}
      >
        <p className="whitespace-pre-wrap">{message.content}</p>
        {isAssistant && message.groundingStatus && message.groundingStatus !== "grounded" && (
          <p className="mt-3 rounded-lg bg-amber-50 px-3 py-2 text-xs leading-5 text-amber-800">
            {message.groundingStatus === "blocked"
              ? (isZh ? "這則要求已被安全規則阻擋。" : "This request was blocked by the safety rules.")
              : (isZh ? "網站資料不足，這則回覆不包含未經證實的規格或承諾。" : "Published site data is insufficient, so this reply avoids unverified specifications or commitments.")}
          </p>
        )}
        {isAssistant && message.groundingStatus === "grounded" && message.claimWarnings && message.claimWarnings.length > 0 && (
          <p className="mt-3 text-xs leading-5 text-amber-700">
            {isZh ? "價格、交期或合規條件仍須由業務依正式文件確認。" : "Pricing, lead time, and compliance terms still require sales confirmation against formal documents."}
          </p>
        )}
        {isAssistant && message.sources && message.sources.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-2">
            {message.sources.slice(0, 2).map((source, index) => (
              source.url ? (
                <a
                  key={`${source.type}-${source.id}`}
                  href={sourceHref(source.url)}
                  title={source.name}
                  className="inline-flex"
                >
                  <Badge variant="info" className="cursor-pointer hover:bg-blue-200">
                    {responseCopy.relatedSource} {index + 1}
                  </Badge>
                </a>
              ) : (
                <Badge key={`${source.type}-${source.id}`} title={source.name} variant="info">
                  {responseCopy.relatedSource} {index + 1}
                </Badge>
              )
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
