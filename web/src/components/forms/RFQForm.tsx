"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { trackRFQStart, trackRFQSubmit, getVisitorId } from "@/lib/analytics";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Loader2, CheckCircle2 } from "lucide-react";
import { useMessageNamespace } from "@/lib/messages";

type OptionItem = {
  value: string;
  label: string;
};

type RFQFormMessages = {
  howOptions: OptionItem[];
  timelineOptions: OptionItem[];
  incotermOptions: OptionItem[];
  successTitle: string;
  referenceNumber: string;
  successDescription: string;
  submitting: string;
  submit: string;
  footerNote: string;
  submitFailed: string;
  unexpectedError: string;
  validationFailed: string;
  challengeRefreshed: string;
  tradeSectionTitle: string;
  labels: {
    fullName: string;
    email: string;
    company: string;
    phone: string;
    country: string;
    jobTitle: string;
    quantity: string;
    specifications: string;
    timeline: string;
    message: string;
    howFound: string;
    consent: string;
    incoterm: string;
    annualVolume: string;
    targetPrice: string;
    trialOrder: string;
  };
  placeholders: {
    quantity: string;
    specifications: string;
    message: string;
    annualVolume: string;
    targetPrice: string;
  };
};

const DRAFT_KEY = "fb_rfq_draft";
const API_BASE = "";
const TURNSTILE_SITE_KEY = process.env.NEXT_PUBLIC_TURNSTILE_SITE_KEY || "";

type TurnstileApi = {
  render: (container: HTMLElement, options: {
    sitekey: string;
    theme: "auto";
    action: string;
    callback: (token: string) => void;
    "expired-callback": () => void;
    "error-callback": () => void;
  }) => string;
  remove: (widgetId: string) => void;
  reset: (widgetId: string) => void;
};

const SELECT_CLS = "flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50 text-foreground";

interface FormState {
  full_name: string; email: string; company_name: string; phone: string;
  country: string; job_title: string; quantity: string; specifications: string;
  timeline: string; message: string; how_did_you_find_us: string; consent: boolean;
  incoterm: string; annual_volume: string; target_price: string; is_trial_order: boolean;
}

const EMPTY_FORM: FormState = {
  full_name: "", email: "", company_name: "", phone: "", country: "", job_title: "",
  quantity: "", specifications: "", timeline: "", message: "", how_did_you_find_us: "", consent: false,
  incoterm: "", annual_volume: "", target_price: "", is_trial_order: false,
};

interface Props {
  preselectedProductIds?: string[];
  preselectedApplicationId?: string;
}

export function RFQForm({ preselectedProductIds = [], preselectedApplicationId }: Props) {
  const copy = useMessageNamespace<RFQFormMessages>("forms.rfq");
  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [rfqNumber, setRfqNumber] = useState("");
  const [error, setError] = useState("");
  const [draftId, setDraftId] = useState<string | null>(null);
  const [draftProductIds, setDraftProductIds] = useState<string[]>([]);
  const [draftApplicationId, setDraftApplicationId] = useState<string | undefined>();
  const [botChallenge, setBotChallenge] = useState("");
  const [turnstileToken, setTurnstileToken] = useState("");
  const [website, setWebsite] = useState("");
  const startedRef = useRef(false);
  const turnstileContainerRef = useRef<HTMLDivElement>(null);
  const turnstileWidgetIdRef = useRef<string | null>(null);

  useEffect(() => {
    try {
      const saved = sessionStorage.getItem(DRAFT_KEY);
      if (saved) { const parsed = JSON.parse(saved) as Partial<FormState>; setForm((prev) => ({ ...prev, ...parsed })); }
    } catch { /* ignore */ }
  }, []);

  const fetchChallenge = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/api/v1/forms/rfq/challenge`);
      if (!response.ok) throw new Error("challenge unavailable");
      const payload = await response.json();
      setBotChallenge(String(payload.challenge || ""));
    } catch {
      setBotChallenge("");
    }
  }, []);

  useEffect(() => { void fetchChallenge(); }, [fetchChallenge]);

  useEffect(() => {
    if (!TURNSTILE_SITE_KEY) return;
    let cancelled = false;
    const turnstileWindow = window as typeof window & { turnstile?: TurnstileApi };
    const renderWidget = () => {
      if (cancelled || !turnstileWindow.turnstile || !turnstileContainerRef.current || turnstileWidgetIdRef.current) return;
      turnstileWidgetIdRef.current = turnstileWindow.turnstile.render(turnstileContainerRef.current, {
        sitekey: TURNSTILE_SITE_KEY,
        theme: "auto",
        action: "rfq_submit",
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

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const serverDraftId = params.get("draft");
    setForm((prev) => ({
      ...prev,
      full_name: params.get("name") || prev.full_name,
      email: params.get("email") || prev.email,
      company_name: params.get("company") || prev.company_name,
      quantity: params.get("quantity") || prev.quantity,
      specifications: params.get("specifications") || prev.specifications,
      message: [params.get("message"), params.get("requirement_summary")]
        .filter(Boolean)
        .join("\n\n") || prev.message,
    }));
    if (!serverDraftId) return;
    const visitorId = getVisitorId();
    fetch(`${API_BASE}/api/v1/chat/handoffs/${encodeURIComponent(serverDraftId)}?visitor_id=${encodeURIComponent(visitorId)}`)
      .then(async (response) => {
        if (!response.ok) throw new Error(copy.submitFailed);
        return response.json();
      })
      .then((payload) => {
        const prefill = payload?.data?.prefill || {};
        setDraftId(serverDraftId);
        setDraftProductIds(Array.isArray(prefill.product_ids) ? prefill.product_ids : []);
        setDraftApplicationId(prefill.application_id || undefined);
        setForm((prev) => ({
          ...prev,
          quantity: prefill.quantity || prev.quantity,
          specifications: prefill.specifications || prev.specifications,
          message: [prefill.message, prefill.requirement_summary].filter(Boolean).join("\n\n") || prev.message,
        }));
      })
      .catch(() => setError(copy.submitFailed));
  }, [copy.submitFailed]);

  function saveDraft(nextForm: FormState) {
    try {
      // RFQ PII should not survive the browser session, and consent must be
      // actively confirmed for each final submission rather than restored.
      sessionStorage.setItem(DRAFT_KEY, JSON.stringify({ ...nextForm, consent: false }));
    } catch { /* ignore quota errors */ }
  }

  function handleChange(e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) {
    const next = { ...form, [e.target.name]: e.target.value };
    setForm(next); saveDraft(next);
    if (!startedRef.current) { startedRef.current = true; trackRFQStart(); }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault(); setError(""); setSubmitting(true);
    try {
      const currentPath = `${window.location.pathname}${window.location.search}`;
      const payload = {
        ...form,
        product_ids: draftProductIds.length ? draftProductIds : preselectedProductIds,
        application_id: draftApplicationId || preselectedApplicationId || undefined,
        draft_id: draftId || undefined,
        visitor_id: getVisitorId(),
        source_page: currentPath,
        bot_challenge: botChallenge || undefined,
        turnstile_token: turnstileToken || undefined,
        website,
      };
      const res = await fetch(`${API_BASE}/api/v1/forms/rfq`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        const detail = data?.detail ?? data?.error;
        const detailText = typeof detail === "string" ? detail.toLowerCase() : "";
        const challengeExpired = detailText.includes("challenge") || detailText.includes("bot verification");
        if (challengeExpired) {
          await fetchChallenge();
          const turnstileWindow = window as typeof window & { turnstile?: TurnstileApi };
          if (turnstileWidgetIdRef.current && turnstileWindow.turnstile) {
            turnstileWindow.turnstile.reset(turnstileWidgetIdRef.current);
            setTurnstileToken("");
          }
          throw new Error(copy.challengeRefreshed);
        }
        if (Array.isArray(detail)) throw new Error(copy.validationFailed);
        throw new Error(copy.submitFailed);
      }
      trackRFQSubmit();
      setRfqNumber(data.rfq_number); setSubmitted(true);
      try { sessionStorage.removeItem(DRAFT_KEY); } catch { /* ignore */ }
    } catch (err) {
      setError(err instanceof Error ? err.message : copy.unexpectedError);
    } finally { setSubmitting(false); }
  }

  if (submitted) {
    return (
      <div className="rounded-lg border border-green-200 bg-green-50 p-8 text-center">
        <CheckCircle2 className="mx-auto mb-4 h-12 w-12 text-green-500" />
        <h2 className="text-xl font-bold text-green-800 mb-2">{copy.successTitle}</h2>
        <p className="text-green-700 mb-1">{copy.referenceNumber} <strong>{rfqNumber}</strong></p>
        <p className="text-sm text-green-600">{copy.successDescription}</p>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      <div className="absolute -left-[10000px] h-px w-px overflow-hidden" aria-hidden="true">
        <Label htmlFor="website">Website</Label>
        <Input id="website" name="website" value={website} onChange={(event) => setWebsite(event.target.value)} tabIndex={-1} autoComplete="off" />
      </div>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="space-y-1.5">
          <Label htmlFor="full_name">{copy.labels.fullName} <span className="text-destructive">*</span></Label>
          <Input id="full_name" name="full_name" value={form.full_name} onChange={handleChange} required />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="email">{copy.labels.email} <span className="text-destructive">*</span></Label>
          <Input id="email" name="email" type="email" value={form.email} onChange={handleChange} required />
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="space-y-1.5">
          <Label htmlFor="company_name">{copy.labels.company} <span className="text-destructive">*</span></Label>
          <Input id="company_name" name="company_name" value={form.company_name} onChange={handleChange} required />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="phone">{copy.labels.phone}</Label>
          <Input id="phone" name="phone" type="tel" value={form.phone} onChange={handleChange} />
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="space-y-1.5">
          <Label htmlFor="country">{copy.labels.country} <span className="text-destructive">*</span></Label>
          <Input id="country" name="country" value={form.country} onChange={handleChange} required />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="job_title">{copy.labels.jobTitle}</Label>
          <Input id="job_title" name="job_title" value={form.job_title} onChange={handleChange} />
        </div>
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="quantity">{copy.labels.quantity}</Label>
        <Input id="quantity" name="quantity" value={form.quantity} onChange={handleChange} placeholder={copy.placeholders.quantity} />
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="specifications">{copy.labels.specifications}</Label>
        <Textarea
          id="specifications" name="specifications" value={form.specifications} onChange={handleChange} rows={4}
          placeholder={copy.placeholders.specifications}
        />
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="timeline">{copy.labels.timeline}</Label>
        <select id="timeline" name="timeline" value={form.timeline} onChange={handleChange} className={SELECT_CLS}>
          {copy.timelineOptions.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
      </div>

      <fieldset className="space-y-4 rounded-lg border bg-muted/20 p-4">
        <legend className="px-1 text-sm font-semibold text-muted-foreground">{copy.tradeSectionTitle}</legend>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div className="space-y-1.5">
            <Label htmlFor="incoterm">{copy.labels.incoterm}</Label>
            <select id="incoterm" name="incoterm" value={form.incoterm} onChange={handleChange} className={SELECT_CLS}>
              {copy.incotermOptions.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="annual_volume">{copy.labels.annualVolume}</Label>
            <Input id="annual_volume" name="annual_volume" value={form.annual_volume} onChange={handleChange} placeholder={copy.placeholders.annualVolume} />
          </div>
        </div>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div className="space-y-1.5">
            <Label htmlFor="target_price">{copy.labels.targetPrice}</Label>
            <Input id="target_price" name="target_price" value={form.target_price} onChange={handleChange} placeholder={copy.placeholders.targetPrice} />
          </div>
          <label className="flex items-center gap-2.5 self-end pb-2 text-sm cursor-pointer">
            <input
              type="checkbox"
              name="is_trial_order"
              checked={form.is_trial_order}
              onChange={(e) => {
                const next = { ...form, is_trial_order: e.target.checked };
                setForm(next); saveDraft(next);
                if (!startedRef.current) { startedRef.current = true; trackRFQStart(); }
              }}
              className="h-4 w-4 rounded border-input text-primary focus:ring-ring"
            />
            <span>{copy.labels.trialOrder}</span>
          </label>
        </div>
      </fieldset>

      <div className="space-y-1.5">
        <Label htmlFor="message">{copy.labels.message}</Label>
        <Textarea
          id="message" name="message" value={form.message} onChange={handleChange} rows={3}
          placeholder={copy.placeholders.message}
        />
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="how_did_you_find_us">{copy.labels.howFound}</Label>
        <select id="how_did_you_find_us" name="how_did_you_find_us" value={form.how_did_you_find_us} onChange={handleChange} className={SELECT_CLS}>
          {copy.howOptions.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
      </div>

      {error && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}

      {TURNSTILE_SITE_KEY && (
        <div ref={turnstileContainerRef} />
      )}

      <label className="flex items-start gap-3 rounded-lg border bg-muted/30 px-4 py-3 text-sm text-muted-foreground cursor-pointer">
        <input
          type="checkbox"
          name="consent"
          checked={form.consent}
          onChange={(e) => {
            const next = { ...form, consent: e.target.checked };
            setForm(next); saveDraft(next);
            if (!startedRef.current) { startedRef.current = true; trackRFQStart(); }
          }}
          required
          className="mt-0.5 h-4 w-4 rounded border-input text-primary focus:ring-ring"
        />
        <span>{copy.labels.consent}</span>
      </label>

      <Button type="submit" size="lg" className="w-full" disabled={submitting || !form.consent || (TURNSTILE_SITE_KEY ? !turnstileToken : false)}>
        {submitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
        {submitting ? copy.submitting : copy.submit}
      </Button>

      <p className="text-xs text-muted-foreground text-center">
        {copy.footerNote}
      </p>
    </form>
  );
}
