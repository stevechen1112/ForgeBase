"use client";

import { usePathname } from "@/i18n/navigation";
import { ChatWidget } from "@/components/chat/ChatWidget";

function stripLocalePrefix(pathname: string): string {
  const path = pathname || "/";
  if (path === "/zh-TW") return "/";
  if (path.startsWith("/zh-TW/")) return path.slice("/zh-TW".length) || "/";
  return path;
}

function pageAlreadyMountsChat(pathname: string): boolean {
  const path = stripLocalePrefix(pathname);
  if (path === "/") return true;
  return path.startsWith("/products") || path.startsWith("/applications") || path.startsWith("/faq");
}

export function LayoutChatWidget() {
  const pathname = usePathname();
  const contextPage = stripLocalePrefix(pathname);
  if (pageAlreadyMountsChat(contextPage)) return null;
  return <ChatWidget contextPage={contextPage} contextEntityType="home" />;
}
