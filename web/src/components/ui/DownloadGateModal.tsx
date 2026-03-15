"use client";
/**
 * 2.1.5 Download Gate Modal
 *
 * Shows a modal requesting name + email (+company) before triggering a PDF download.
 * On successful submission, the backend creates/updates the Contact, fires a
 * spec_download tracking event, and returns the authorised download URL.
 */
import { useState } from "react";
import { getVisitorId } from "@/lib/analytics";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Download, Loader2 } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

interface Doc {
  id: string;
  title: string | null;
  seo_title: string | null;
  public_url: string;
  requires_gate?: boolean;
}

interface Props {
  productId: string;
  productName: string;
  docs: Doc[];
}

export function DownloadGateModal({ productId, productName, docs }: Props) {
  const [open, setOpen] = useState(false);
  const [selectedDoc, setSelectedDoc] = useState<Doc | null>(null);
  const [form, setForm] = useState({ full_name: "", email: "", company_name: "" });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  if (docs.length === 0) return null;

  const gatedDocs = docs.filter((d) => d.requires_gate !== false); // gate by default
  const directDocs = docs.filter((d) => d.requires_gate === false);

  const handleOpen = (doc?: Doc) => {
    setSelectedDoc(doc ?? gatedDocs[0] ?? docs[0]);
    setOpen(true);
    setError("");
  };

  const handleSubmit = async () => {
    if (!form.full_name.trim() || !form.email.trim()) {
      setError("Please fill in your name and email.");
      return;
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) {
      setError("Please enter a valid email address.");
      return;
    }
    setSubmitting(true);
    setError("");
    try {
      const res = await fetch(`${API_BASE}/api/v1/forms/download-gate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          full_name: form.full_name.trim(),
          email: form.email.trim().toLowerCase(),
          company_name: form.company_name.trim() || undefined,
          asset_id: selectedDoc?.id,
          visitor_id: getVisitorId(),
          source_page:
            typeof window !== "undefined"
              ? `${window.location.pathname}${window.location.search}`
              : `product:${productId}`,
        }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Submission failed");
      }

      const data = await res.json();
      const url = data.download_url ?? selectedDoc?.public_url;
      if (url) {
        const a = document.createElement("a");
        a.href = url;
        a.download = data.filename ?? selectedDoc?.seo_title ?? selectedDoc?.title ?? "document";
        a.rel = "noopener noreferrer";
        a.target = "_blank";
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
      }

      setOpen(false);
      setForm({ full_name: "", email: "", company_name: "" });
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Something went wrong. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <>
      {/* Trigger buttons */}
      {gatedDocs.length === 0 && directDocs.length > 0 ? (
        // All docs are direct download (no gate)
        directDocs.length === 1 ? (
          <Button asChild variant="outline" size="default">
            <a href={directDocs[0].public_url} target="_blank" rel="noopener noreferrer">
              <Download className="mr-2 h-4 w-4" />
              {directDocs[0].seo_title ?? directDocs[0].title ?? "Download Spec Sheet"}
            </a>
          </Button>
        ) : (
          <div className="relative group">
            <Button variant="outline">
              <Download className="mr-2 h-4 w-4" />
              Downloads ▾
            </Button>
            <div className="absolute left-0 top-full mt-1 bg-popover border rounded-lg shadow-lg z-10 min-w-48 hidden group-hover:block">
              {directDocs.map((doc) => (
                <a
                  key={doc.id}
                  href={doc.public_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="block w-full text-left px-4 py-2 text-sm text-foreground hover:bg-muted first:rounded-t-lg last:rounded-b-lg"
                >
                  {doc.seo_title ?? doc.title ?? "Spec Sheet"}
                </a>
              ))}
            </div>
          </div>
        )
      ) : gatedDocs.length === 1 && directDocs.length === 0 ? (
        <Button variant="outline" onClick={() => handleOpen(gatedDocs[0])}>
          <Download className="mr-2 h-4 w-4" />
          Download Spec Sheet
        </Button>
      ) : (
        <div className="relative group">
          <Button variant="outline">
            <Download className="mr-2 h-4 w-4" />
            Downloads ▾
          </Button>
          <div className="absolute left-0 top-full mt-1 bg-popover border rounded-lg shadow-lg z-10 min-w-56 hidden group-hover:block">
            {gatedDocs.map((doc) => (
              <button
                key={doc.id}
                onClick={() => handleOpen(doc)}
                className="w-full text-left px-4 py-2 text-sm text-foreground hover:bg-muted first:rounded-t-lg last:rounded-b-lg flex items-center gap-2"
              >
                <span>🔒</span>
                {doc.seo_title ?? doc.title ?? "Spec Sheet"}
              </button>
            ))}
            {directDocs.map((doc) => (
              <a
                key={doc.id}
                href={doc.public_url}
                target="_blank"
                rel="noopener noreferrer"
                className="block w-full text-left px-4 py-2 text-sm text-foreground hover:bg-muted first:rounded-t-lg last:rounded-b-lg flex items-center gap-2"
              >
                <span>📄</span>
                {doc.seo_title ?? doc.title ?? "Spec Sheet"}
              </a>
            ))}
          </div>
        </div>
      )}

      {/* Modal */}
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Download Spec Sheet</DialogTitle>
            <DialogDescription>
              {selectedDoc?.seo_title ?? selectedDoc?.title ?? productName}
            </DialogDescription>
          </DialogHeader>

          <p className="text-sm text-muted-foreground">
            Enter your details to get instant access to the full specification document.
          </p>

          <div className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="dg-name">Full Name *</Label>
              <Input
                id="dg-name"
                type="text"
                value={form.full_name}
                onChange={(e) => setForm({ ...form, full_name: e.target.value })}
                autoComplete="name"
                placeholder="John Smith"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="dg-email">Business Email *</Label>
              <Input
                id="dg-email"
                type="email"
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                autoComplete="email"
                placeholder="you@company.com"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="dg-company">Company</Label>
              <Input
                id="dg-company"
                type="text"
                value={form.company_name}
                onChange={(e) => setForm({ ...form, company_name: e.target.value })}
                autoComplete="organization"
                placeholder="Your company (optional)"
              />
            </div>

            {error && (
              <Alert variant="destructive">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            <Button onClick={handleSubmit} disabled={submitting} className="w-full">
              {submitting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Submitting…
                </>
              ) : (
                <>
                  <Download className="mr-2 h-4 w-4" />
                  Download Now
                </>
              )}
            </Button>

            <p className="text-xs text-muted-foreground text-center">
              We respect your privacy. Your information will not be shared.
            </p>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}
