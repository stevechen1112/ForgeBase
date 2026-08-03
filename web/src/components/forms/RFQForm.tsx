"use client";
import { useEffect, useRef, useState } from "react";
import { trackRFQStart, trackRFQSubmit, getVisitorId } from "@/lib/analytics";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Loader2, CheckCircle2 } from "lucide-react";
import { useMessageNamespace } from "@/lib/messages";
import { withTenantHeaders } from "@/lib/tenant";

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
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

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
  const startedRef = useRef(false);

  useEffect(() => {
    try {
      const saved = localStorage.getItem(DRAFT_KEY);
      if (saved) { const parsed = JSON.parse(saved) as Partial<FormState>; setForm((prev) => ({ ...prev, ...parsed })); }
    } catch { /* ignore */ }
  }, []);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    setForm((prev) => ({
      ...prev,
      full_name: params.get("name") || prev.full_name,
      email: params.get("email") || prev.email,
      company_name: params.get("company") || prev.company_name,
    }));
  }, []);

  function saveDraft(nextForm: FormState) {
    try { localStorage.setItem(DRAFT_KEY, JSON.stringify(nextForm)); } catch { /* ignore quota errors */ }
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
        product_ids: preselectedProductIds,
        application_id: preselectedApplicationId || undefined,
        visitor_id: getVisitorId(),
        source_page: currentPath,
      };
      const res = await fetch(`${API_BASE}/api/v1/forms/rfq`, {
        method: "POST",
        headers: withTenantHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || copy.submitFailed);
      trackRFQSubmit();
      setRfqNumber(data.rfq_number); setSubmitted(true);
      try { localStorage.removeItem(DRAFT_KEY); } catch { /* ignore */ }
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
        <Label>{copy.labels.timeline}</Label>
        <select name="timeline" value={form.timeline} onChange={handleChange} className={SELECT_CLS}>
          {copy.timelineOptions.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
      </div>

      <fieldset className="space-y-4 rounded-lg border bg-muted/20 p-4">
        <legend className="px-1 text-sm font-semibold text-muted-foreground">{copy.tradeSectionTitle}</legend>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div className="space-y-1.5">
            <Label>{copy.labels.incoterm}</Label>
            <select name="incoterm" value={form.incoterm} onChange={handleChange} className={SELECT_CLS}>
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
        <Label>{copy.labels.howFound}</Label>
        <select name="how_did_you_find_us" value={form.how_did_you_find_us} onChange={handleChange} className={SELECT_CLS}>
          {copy.howOptions.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
      </div>

      {error && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}

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

      <Button type="submit" size="lg" className="w-full" disabled={submitting || !form.consent}>
        {submitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
        {submitting ? copy.submitting : copy.submit}
      </Button>

      <p className="text-xs text-muted-foreground text-center">
        {copy.footerNote}
      </p>
    </form>
  );
}
