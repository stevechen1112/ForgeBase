"use client";
import { useState, useRef } from "react";
import { trackFormStart, trackFormSubmit, getVisitorId } from "@/lib/analytics";
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

type ContactFormMessages = {
  successTitle: string;
  successDescription: string;
  sending: string;
  submit: string;
  submitFailed: string;
  unexpectedError: string;
  labels: {
    fullName: string;
    email: string;
    company: string;
    country: string;
    jobTitle: string;
    phone: string;
    message: string;
    howFound: string;
  };
  placeholders: {
    fullName: string;
    email: string;
    company: string;
    country: string;
    jobTitle: string;
    phone: string;
    message: string;
  };
};

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

const SELECT_CLS = "flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50 text-foreground";

export function ContactForm() {
  const copy = useMessageNamespace<ContactFormMessages>("forms.contact");
  const howOptions = useMessageNamespace<OptionItem[]>("forms.howOptions");
  const [form, setForm] = useState({
    full_name: "", email: "", company_name: "", phone: "",
    country: "", job_title: "", how_did_you_find_us: "", message: "",
  });
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState("");
  const startedRef = useRef(false);

  function handleChange(e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));
    if (!startedRef.current) { startedRef.current = true; trackFormStart("contact"); }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault(); setError(""); setSubmitting(true);
    try {
      const currentPath = `${window.location.pathname}${window.location.search}`;
      const payload = { ...form, visitor_id: getVisitorId(), source_page: currentPath };
      const res = await fetch(`${API_BASE}/api/v1/forms/contact`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || copy.submitFailed);
      trackFormSubmit("contact");
      setSubmitted(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : copy.unexpectedError);
    } finally { setSubmitting(false); }
  }

  if (submitted) {
    return (
      <div className="rounded-xl border border-green-200 bg-green-50 p-6 text-center">
        <CheckCircle2 className="mx-auto mb-3 h-10 w-10 text-green-500" />
        <h3 className="font-semibold text-green-800 text-lg mb-1">{copy.successTitle}</h3>
        <p className="text-sm text-green-700">
          {copy.successDescription}
        </p>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="space-y-1.5">
        <Label htmlFor="full_name">{copy.labels.fullName} <span className="text-destructive">*</span></Label>
        <Input id="full_name" name="full_name" required value={form.full_name} onChange={handleChange} placeholder={copy.placeholders.fullName} />
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="email">{copy.labels.email} <span className="text-destructive">*</span></Label>
        <Input id="email" name="email" type="email" required value={form.email} onChange={handleChange} placeholder={copy.placeholders.email} />
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="space-y-1.5">
          <Label htmlFor="company_name">{copy.labels.company}</Label>
          <Input id="company_name" name="company_name" value={form.company_name} onChange={handleChange} placeholder={copy.placeholders.company} />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="country">{copy.labels.country}</Label>
          <Input id="country" name="country" value={form.country} onChange={handleChange} placeholder={copy.placeholders.country} />
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="space-y-1.5">
          <Label htmlFor="job_title">{copy.labels.jobTitle}</Label>
          <Input id="job_title" name="job_title" value={form.job_title} onChange={handleChange} placeholder={copy.placeholders.jobTitle} />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="phone">{copy.labels.phone}</Label>
          <Input id="phone" name="phone" value={form.phone} onChange={handleChange} placeholder={copy.placeholders.phone} />
        </div>
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="message">{copy.labels.message} <span className="text-destructive">*</span></Label>
        <Textarea id="message" name="message" required rows={4} value={form.message} onChange={handleChange} placeholder={copy.placeholders.message} />
      </div>

      <div className="space-y-1.5">
        <Label>{copy.labels.howFound}</Label>
        <select id="how_did_you_find_us" name="how_did_you_find_us" value={form.how_did_you_find_us} onChange={handleChange} className={SELECT_CLS}>
          {howOptions.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
      </div>

      {error && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}

      <Button type="submit" size="lg" className="w-full" disabled={submitting}>
        {submitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
        {submitting ? copy.sending : copy.submit}
      </Button>
    </form>
  );
}
