"use client";

import { useEffect, useState } from "react";
import { hasAnalyticsConsent, revokeAnalyticsConsent, setAnalyticsConsent } from "@/lib/analytics";

export function ConsentPreferences({ locale }: { locale: string }) {
  const [granted, setGranted] = useState(false);
  const [saved, setSaved] = useState(false);
  const zh = locale.toLowerCase().startsWith("zh");

  useEffect(() => setGranted(hasAnalyticsConsent()), []);

  const choose = (allow: boolean) => {
    if (allow) setAnalyticsConsent(true);
    else revokeAnalyticsConsent();
    setGranted(allow);
    setSaved(true);
  };

  return (
    <section className="not-prose mt-8 rounded-lg border border-gray-300 bg-white p-5" aria-labelledby="analytics-preferences-title">
      <h2 id="analytics-preferences-title" className="text-lg font-semibold text-gray-900">
        {zh ? "分析資料偏好" : "Analytics preferences"}
      </h2>
      <p className="mt-2 text-sm text-gray-600">
        {zh
          ? `目前狀態：${granted ? "已允許匿名分析" : "僅必要功能"}。撤回後，伺服器會刪除這個瀏覽器識別碼所連結的分析事件與工作階段；已送出的詢價與客服紀錄不受影響。`
          : `Current status: ${granted ? "anonymous analytics allowed" : "essential functions only"}. Revoking deletes analytics events and sessions tied to this browser identifier; submitted RFQs and chat records are preserved.`}
      </p>
      <div className="mt-4 flex flex-wrap gap-3">
        <button type="button" onClick={() => choose(false)} className="rounded border border-gray-400 px-4 py-2 text-sm font-medium text-gray-800">
          {zh ? "撤回分析同意" : "Revoke analytics"}
        </button>
        <button type="button" onClick={() => choose(true)} className="rounded bg-gray-900 px-4 py-2 text-sm font-medium text-white">
          {zh ? "允許匿名分析" : "Allow analytics"}
        </button>
      </div>
      {saved && <p role="status" className="mt-3 text-sm text-green-700">{zh ? "偏好已儲存。" : "Preference saved."}</p>}
    </section>
  );
}
