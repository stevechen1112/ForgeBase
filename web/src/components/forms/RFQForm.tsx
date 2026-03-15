"use client";
import { useEffect, useRef, useState } from "react";
import { trackRFQStart, trackRFQSubmit, getVisitorId } from "@/lib/analytics";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Loader2, CheckCircle2 } from "lucide-react";

const DRAFT_KEY = "fb_rfq_draft";
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

const SELECT_CLS = "flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50 text-foreground";

const HOW_OPTIONS = [
  { value: "", label: "How did you find us?" },
  { value: "google", label: "Google Search" },
  { value: "exhibition", label: "Exhibition" },
  { value: "referral", label: "Referral" },
  { value: "other", label: "Other" },
];

const TIMELINE_OPTIONS = [
  { value: "", label: "Delivery Timeline" },
  { value: "immediate", label: "Immediate" },
  { value: "1-3 months", label: "1-3 months" },
  { value: "3-6 months", label: "3-6 months" },
  { value: "evaluating", label: "Evaluating" },
];

interface FormState {
  full_name: string; email: string; company_name: string; phone: string;
  country: string; job_title: string; quantity: string; specifications: string;
  timeline: string; message: string; how_did_you_find_us: string; consent: boolean;
}

const EMPTY_FORM: FormState = {
  full_name: "", email: "", company_name: "", phone: "", country: "", job_title: "",
  quantity: "", specifications: "", timeline: "", message: "", how_did_you_find_us: "", consent: false,
};

interface Props {
  preselectedProductIds?: string[];
  preselectedApplicationId?: string;
}

export function RFQForm({ preselectedProductIds = [], preselectedApplicationId }: Props) {
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
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Submission failed. Please try again.");
      trackRFQSubmit();
      setRfqNumber(data.rfq_number); setSubmitted(true);
      try { localStorage.removeItem(DRAFT_KEY); } catch { /* ignore */ }
    } catch (err) {
      setError(err instanceof Error ? err.message : "An unexpected error occurred.");
    } finally { setSubmitting(false); }
  }

  if (submitted) {
    return (
      <div className="rounded-lg border border-green-200 bg-green-50 p-8 text-center">
        <CheckCircle2 className="mx-auto mb-4 h-12 w-12 text-green-500" />
        <h2 className="text-xl font-bold text-green-800 mb-2">RFQ Submitted Successfully</h2>
        <p className="text-green-700 mb-1">Your reference number: <strong>{rfqNumber}</strong></p>
        <p className="text-sm text-green-600">Our team will review your request and get back to you within 1–2 business days.</p>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="space-y-1.5">
          <Label htmlFor="full_name">Full Name <span className="text-destructive">*</span></Label>
          <Input id="full_name" name="full_name" value={form.full_name} onChange={handleChange} required />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="email">Business Email <span className="text-destructive">*</span></Label>
          <Input id="email" name="email" type="email" value={form.email} onChange={handleChange} required />
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="space-y-1.5">
          <Label htmlFor="company_name">Company Name <span className="text-destructive">*</span></Label>
          <Input id="company_name" name="company_name" value={form.company_name} onChange={handleChange} required />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="phone">Phone / WhatsApp</Label>
          <Input id="phone" name="phone" type="tel" value={form.phone} onChange={handleChange} />
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="space-y-1.5">
          <Label htmlFor="country">Country / Region <span className="text-destructive">*</span></Label>
          <Input id="country" name="country" value={form.country} onChange={handleChange} required />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="job_title">Job Title</Label>
          <Input id="job_title" name="job_title" value={form.job_title} onChange={handleChange} />
        </div>
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="quantity">Quantity Required</Label>
        <Input id="quantity" name="quantity" value={form.quantity} onChange={handleChange} placeholder="e.g. 500 pcs, 1000 sets" />
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="specifications">Technical Specifications / Requirements</Label>
        <Textarea
          id="specifications" name="specifications" value={form.specifications} onChange={handleChange} rows={4}
          placeholder="Describe your dimensional requirements, materials, pressure ratings, or any other specs..."
        />
      </div>

      <div className="space-y-1.5">
        <Label>Delivery Timeline</Label>
        <select name="timeline" value={form.timeline} onChange={handleChange} className={SELECT_CLS}>
          {TIMELINE_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="message">Additional Message</Label>
        <Textarea
          id="message" name="message" value={form.message} onChange={handleChange} rows={3}
          placeholder="Any other information that would help us prepare a more accurate quotation..."
        />
      </div>

      <div className="space-y-1.5">
        <Label>How did you find us?</Label>
        <select name="how_did_you_find_us" value={form.how_did_you_find_us} onChange={handleChange} className={SELECT_CLS}>
          {HOW_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
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
        <span>I agree to the Privacy Policy and consent to the processing of my enquiry data. *</span>
      </label>

      <Button type="submit" size="lg" className="w-full" disabled={submitting || !form.consent}>
        {submitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
        {submitting ? "Submitting…" : "Submit RFQ Request"}
      </Button>

      <p className="text-xs text-muted-foreground text-center">
        By submitting this form you agree to our Privacy Policy. We will never share your data with third parties.
      </p>
    </form>
  );
}
