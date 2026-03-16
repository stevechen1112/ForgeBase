"use client";
import { useState, useRef } from "react";
import { trackFormStart, trackFormSubmit, getVisitorId } from "@/lib/analytics";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Loader2, CheckCircle2 } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

const SELECT_CLS = "flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50 text-foreground";

const HOW_OPTIONS = [
  { value: "", label: "How did you find us? (optional)" },
  { value: "google", label: "Google Search" },
  { value: "linkedin", label: "LinkedIn" },
  { value: "trade_show", label: "Trade Show / Exhibition" },
  { value: "referral", label: "Referral" },
  { value: "direct", label: "Direct / Already knew" },
  { value: "email", label: "Email Newsletter" },
  { value: "other", label: "Other" },
];

export function ContactForm() {
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
      if (!res.ok) throw new Error(data.detail || "Submission failed. Please try again.");
      trackFormSubmit("contact");
      setSubmitted(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "An unexpected error occurred.");
    } finally { setSubmitting(false); }
  }

  if (submitted) {
    return (
      <div className="rounded-xl border border-green-200 bg-green-50 p-6 text-center">
        <CheckCircle2 className="mx-auto mb-3 h-10 w-10 text-green-500" />
        <h3 className="font-semibold text-green-800 text-lg mb-1">Message Sent!</h3>
        <p className="text-sm text-green-700">
          Thank you for reaching out. We&apos;ll get back to you within one business day.
        </p>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="space-y-1.5">
        <Label htmlFor="full_name">Name <span className="text-destructive">*</span></Label>
        <Input id="full_name" name="full_name" required value={form.full_name} onChange={handleChange} placeholder="Your full name" />
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="email">Email <span className="text-destructive">*</span></Label>
        <Input id="email" name="email" type="email" required value={form.email} onChange={handleChange} placeholder="your@email.com" />
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="space-y-1.5">
          <Label htmlFor="company_name">Company</Label>
          <Input id="company_name" name="company_name" value={form.company_name} onChange={handleChange} placeholder="Distributor, importer, brand, or factory name" />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="country">Country</Label>
          <Input id="country" name="country" value={form.country} onChange={handleChange} placeholder="e.g. United States" />
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="space-y-1.5">
          <Label htmlFor="job_title">Job Title</Label>
          <Input id="job_title" name="job_title" value={form.job_title} onChange={handleChange} placeholder="e.g. Procurement Manager" />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="phone">Phone / WhatsApp</Label>
          <Input id="phone" name="phone" value={form.phone} onChange={handleChange} placeholder="Optional, for faster follow-up" />
        </div>
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="message">Message <span className="text-destructive">*</span></Label>
        <Textarea id="message" name="message" required rows={4} value={form.message} onChange={handleChange} placeholder="Tell us what tool line, application, packaging need, or sourcing challenge you want to discuss..." />
      </div>

      <div className="space-y-1.5">
        <Label>How did you find us?</Label>
        <select id="how_did_you_find_us" name="how_did_you_find_us" value={form.how_did_you_find_us} onChange={handleChange} className={SELECT_CLS}>
          {HOW_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
      </div>

      {error && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}

      <Button type="submit" size="lg" className="w-full" disabled={submitting}>
        {submitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
        {submitting ? "Sending…" : "Send Enquiry"}
      </Button>
    </form>
  );
}
