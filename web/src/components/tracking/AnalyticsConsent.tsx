"use client";

import { useEffect, useState } from "react";
import { hasAnalyticsConsent, setAnalyticsConsent } from "@/lib/analytics";

type Props = { measurementId?: string };

function loadGoogleAnalytics(measurementId: string) {
  if (document.querySelector(`script[data-forgebase-ga="${measurementId}"]`)) return;
  const script = document.createElement("script");
  script.async = true;
  script.src = `https://www.googletagmanager.com/gtag/js?id=${encodeURIComponent(measurementId)}`;
  script.dataset.forgebaseGa = measurementId;
  document.head.appendChild(script);
  window.dataLayer = window.dataLayer || [];
  window.gtag = (...args: unknown[]) => window.dataLayer?.push(args);
  window.gtag("js", new Date());
  window.gtag("config", measurementId, { send_page_view: false });
}

export function AnalyticsConsent({ measurementId }: Props) {
  const [choiceMade, setChoiceMade] = useState(true);
  const [locale, setLocale] = useState("en");

  useEffect(() => {
    setLocale(document.documentElement.lang || "en");
    const choice = document.cookie.match(/(?:^|;\s*)fb_analytics_consent=([^;]*)/)?.[1];
    setChoiceMade(choice === "granted" || choice === "denied");
    if (hasAnalyticsConsent() && measurementId) loadGoogleAnalytics(measurementId);
  }, [measurementId]);

  const choose = (granted: boolean) => {
    setAnalyticsConsent(granted);
    setChoiceMade(true);
    if (granted && measurementId) loadGoogleAnalytics(measurementId);
  };

  if (choiceMade) return null;
  const zh = locale.toLowerCase().startsWith("zh");
  return (
    <aside className="fixed bottom-4 left-4 z-40 w-[min(calc(100vw-6.5rem),28rem)] max-w-md rounded-lg border bg-background p-4 shadow-xl" role="dialog" aria-label={zh ? "分析 Cookie 選擇" : "Analytics cookie choice"}>
      <p className="text-sm text-foreground">
        {zh
          ? "我們只會在您同意後使用分析 Cookie，了解網站使用情況並改善內容。詢價與客服所需的工作階段識別不會用於跨次追蹤。"
          : "We use analytics cookies only after consent to understand site usage and improve content. Session identity needed for RFQ and chat is not used for cross-visit tracking."}
      </p>
      <div className="mt-3 flex justify-end gap-2">
        <button className="rounded border px-4 py-2 text-sm" onClick={() => choose(false)}>
          {zh ? "僅必要功能" : "Essential only"}
        </button>
        <button className="rounded bg-primary px-4 py-2 text-sm text-primary-foreground" onClick={() => choose(true)}>
          {zh ? "同意分析" : "Allow analytics"}
        </button>
      </div>
    </aside>
  );
}
