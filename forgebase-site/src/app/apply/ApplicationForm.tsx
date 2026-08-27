"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { ArrowRight, CheckCircle2, Loader2 } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";
const TURNSTILE_SITE_KEY = process.env.NEXT_PUBLIC_TURNSTILE_SITE_KEY || "";

type TurnstileApi = {
  render: (container: HTMLElement, options: {
    sitekey: string;
    theme: "light";
    action: string;
    callback: (token: string) => void;
    "expired-callback": () => void;
    "error-callback": () => void;
  }) => string;
  remove: (widgetId: string) => void;
  reset: (widgetId: string) => void;
};

const EMPTY_FORM = {
  company_name: "",
  website_url: "",
  contact_name: "",
  work_email: "",
  phone: "",
  job_title: "",
  industry: "",
  target_markets: "",
  current_situation: "evaluating",
  requested_scope: "",
  preferred_language: "zh-TW",
  consent: false,
};

export function ApplicationForm() {
  const [form, setForm] = useState(EMPTY_FORM);
  const [botChallenge, setBotChallenge] = useState("");
  const [turnstileToken, setTurnstileToken] = useState("");
  const [website, setWebsite] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [applicationNumber, setApplicationNumber] = useState("");
  const [error, setError] = useState("");
  const turnstileContainerRef = useRef<HTMLDivElement>(null);
  const turnstileWidgetIdRef = useRef<string | null>(null);

  const fetchChallenge = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/api/v1/forms/adoption/challenge`, { cache: "no-store" });
      if (!response.ok) throw new Error("challenge unavailable");
      const payload = await response.json();
      setBotChallenge(String(payload.challenge || ""));
    } catch {
      setBotChallenge("");
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => { void fetchChallenge(); }, 0);
    return () => window.clearTimeout(timer);
  }, [fetchChallenge]);

  useEffect(() => {
    if (!TURNSTILE_SITE_KEY) return;
    let cancelled = false;
    const turnstileWindow = window as typeof window & { turnstile?: TurnstileApi };
    const renderWidget = () => {
      if (cancelled || !turnstileWindow.turnstile || !turnstileContainerRef.current || turnstileWidgetIdRef.current) return;
      turnstileWidgetIdRef.current = turnstileWindow.turnstile.render(turnstileContainerRef.current, {
        sitekey: TURNSTILE_SITE_KEY,
        theme: "light",
        action: "adoption_submit",
        callback: setTurnstileToken,
        "expired-callback": () => setTurnstileToken(""),
        "error-callback": () => setTurnstileToken(""),
      });
    };
    let script = document.querySelector<HTMLScriptElement>('script[data-forgebase-turnstile="true"]');
    if (!script) {
      script = document.createElement("script");
      script.src = "https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit";
      script.async = true;
      script.defer = true;
      script.dataset.forgebaseTurnstile = "true";
      document.head.appendChild(script);
    }
    if (turnstileWindow.turnstile) renderWidget();
    else script.addEventListener("load", renderWidget, { once: true });
    return () => {
      cancelled = true;
      script?.removeEventListener("load", renderWidget);
      if (turnstileWidgetIdRef.current && turnstileWindow.turnstile) {
        turnstileWindow.turnstile.remove(turnstileWidgetIdRef.current);
        turnstileWidgetIdRef.current = null;
      }
    };
  }, []);

  function updateField(name: keyof typeof EMPTY_FORM, value: string | boolean) {
    setForm((current) => ({ ...current, [name]: value }));
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      const response = await fetch(`${API_BASE}/api/v1/forms/adoption`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...form,
          website_url: form.website_url || undefined,
          phone: form.phone || undefined,
          job_title: form.job_title || undefined,
          target_markets: form.target_markets || undefined,
          source_page: window.location.pathname,
          bot_challenge: botChallenge || undefined,
          turnstile_token: turnstileToken || undefined,
          website,
        }),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        const detail = typeof payload?.detail === "string" ? payload.detail.toLowerCase() : "";
        if (detail.includes("challenge") || detail.includes("bot verification")) {
          await fetchChallenge();
          const turnstileWindow = window as typeof window & { turnstile?: TurnstileApi };
          if (turnstileWidgetIdRef.current && turnstileWindow.turnstile) {
            turnstileWindow.turnstile.reset(turnstileWidgetIdRef.current);
            setTurnstileToken("");
          }
          throw new Error("驗證已更新，請確認欄位後再送出一次。");
        }
        throw new Error("目前無法送出申請，請稍後再試。");
      }
      setApplicationNumber(String(payload.application_number || ""));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "目前無法送出申請，請稍後再試。");
    } finally {
      setSubmitting(false);
    }
  }

  if (applicationNumber) {
    return (
      <div className="application-success" role="status">
        <CheckCircle2 size={46} />
        <span>APPLICATION RECEIVED</span>
        <h2>申請資料已收到</h2>
        <p>參考編號：<strong>{applicationNumber}</strong></p>
        <p>這代表資料已進入導入評估清單，不代表已受理、已建立帳號、已開始試用，或已承諾價格與交付時間。ForgeBase 團隊會先確認目前測試範圍是否適合。</p>
        <Link href="/" className="button button-secondary">返回 ForgeBase 首頁</Link>
      </div>
    );
  }

  return (
    <form className="application-form" onSubmit={handleSubmit}>
      <div className="honeypot" aria-hidden="true">
        <label htmlFor="website">Website</label>
        <input id="website" name="website" value={website} onChange={(event) => setWebsite(event.target.value)} tabIndex={-1} autoComplete="off" />
      </div>

      <div className="form-section-heading"><span>01</span><div><h2>公司與聯絡資料</h2><p>用來判斷網站類型與後續評估方式。</p></div></div>
      <div className="form-grid">
        <label><span>公司名稱 *</span><input value={form.company_name} onChange={(event) => updateField("company_name", event.target.value)} maxLength={200} required /></label>
        <label><span>產業類別 *</span><input value={form.industry} onChange={(event) => updateField("industry", event.target.value)} maxLength={120} placeholder="例如：手工具、機械設備、電子零組件" required /></label>
        <label className="form-wide"><span>目前網站</span><input type="url" value={form.website_url} onChange={(event) => updateField("website_url", event.target.value)} maxLength={500} placeholder="https://（尚無網站可留白）" /></label>
        <label><span>聯絡人姓名 *</span><input value={form.contact_name} onChange={(event) => updateField("contact_name", event.target.value)} maxLength={100} required /></label>
        <label><span>公司 Email *</span><input type="email" value={form.work_email} onChange={(event) => updateField("work_email", event.target.value)} maxLength={254} required /></label>
        <label><span>職稱</span><input value={form.job_title} onChange={(event) => updateField("job_title", event.target.value)} maxLength={100} /></label>
        <label><span>電話</span><input type="tel" value={form.phone} onChange={(event) => updateField("phone", event.target.value)} maxLength={50} /></label>
      </div>

      <div className="form-section-heading"><span>02</span><div><h2>目前情況與希望處理的問題</h2><p>不需要先決定方案；請描述真實狀況即可。</p></div></div>
      <div className="form-grid">
        <label><span>目前情況 *</span><select value={form.current_situation} onChange={(event) => updateField("current_situation", event.target.value)} required><option value="evaluating">先了解是否適合</option><option value="no_site">目前沒有網站</option><option value="replace_site">準備重做現有網站</option><option value="improve_site">希望改善現有網站</option></select></label>
        <label><span>主要目標市場</span><input value={form.target_markets} onChange={(event) => updateField("target_markets", event.target.value)} maxLength={500} placeholder="例如：歐洲、美國、日本" /></label>
        <label><span>偏好溝通語言</span><select value={form.preferred_language} onChange={(event) => updateField("preferred_language", event.target.value)}><option value="zh-TW">繁體中文</option><option value="en">English</option></select></label>
        <label className="form-wide"><span>希望網站協助處理哪些問題？*</span><textarea value={form.requested_scope} onChange={(event) => updateField("requested_scope", event.target.value)} minLength={20} maxLength={4000} rows={7} placeholder="例如：產品很多但客戶不容易找到、詢價資料經常不完整、公司內部無法自行更新產品……" required /></label>
      </div>

      {TURNSTILE_SITE_KEY && <div ref={turnstileContainerRef} className="turnstile-slot" />}
      {error && <p className="form-error" role="alert">{error}</p>}
      <label className="consent-row"><input type="checkbox" checked={form.consent} onChange={(event) => updateField("consent", event.target.checked)} required /><span>我同意 ForgeBase 為了評估產品測試與導入適配性保存並檢視上述資料。我了解送出申請不代表受理、試用、報價或交付承諾。詳見 <Link href="/privacy">資料使用說明</Link>。</span></label>
      <button className="button button-primary form-submit" type="submit" disabled={submitting || !form.consent || !botChallenge || (TURNSTILE_SITE_KEY ? !turnstileToken : false)}>{submitting ? <><Loader2 className="spinner" size={17} />送出中…</> : <>送出導入評估申請 <ArrowRight size={17} /></>}</button>
      <p className="form-footnote">目前為限量產品測試。實際是否進入下一步、可提供的範圍、費用與時程，均需另行確認。</p>
    </form>
  );
}
