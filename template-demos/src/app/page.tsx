import Link from "next/link";
import { ArrowUpRight, Braces, DatabaseZap, ShieldCheck } from "lucide-react";
import { DemoNotice } from "@/components/DemoNotice";
import { templateRegistry } from "@/templates/registry";

export default function TemplateGalleryPage() {
  return (
    <main className="gallery-shell">
      <header className="gallery-header">
        <Link href="/" className="gallery-brand">FORGEBASE <span>/ TEMPLATE LAB</span></Link>
        <DemoNotice compact />
      </header>

      <section className="gallery-hero">
        <p className="eyebrow">B2B INDUSTRY TEMPLATE SYSTEM</p>
        <h1>One data language.<br /><em>Different buying experiences.</em></h1>
        <p className="gallery-intro">Each concept is designed around how a specific B2B buyer evaluates risk. Shared contracts keep future ForgeBase integration predictable; the visual system remains independent.</p>
        <div className="contract-strip">
          <span><Braces size={18} /> Typed data contract</span>
          <span><DatabaseZap size={18} /> Local demo data only</span>
          <span><ShieldCheck size={18} /> No tracking or submission</span>
        </div>
      </section>

      <section className="template-grid" aria-label="Industry templates">
        {templateRegistry.map((template, index) => (
          <article className={`template-card card-${index + 1}`} key={template.slug} style={{ "--accent": template.accent } as React.CSSProperties}>
            <div className="template-card-top">
              <span className={`status ${template.status}`}>{template.status}</span>
              <span className="template-number">0{index + 1}</span>
            </div>
            <p className="template-industry">{template.industry}</p>
            <h2>{template.name}</h2>
            <p>{template.summary}</p>
            <div className="buyer-list">
              {template.buyerRoles.map((role) => <span key={role}>{role}</span>)}
            </div>
            {template.status === "ready" ? (
              <Link className="template-link" href={`/templates/${template.slug}/`}>
                Open live preview <ArrowUpRight aria-hidden="true" size={18} />
              </Link>
            ) : (
              <span className="template-link disabled">Design brief registered</span>
            )}
          </article>
        ))}
      </section>

      <footer className="gallery-footer">
        <p>ForgeBase Template Lab · Static previews for design selection</p>
        <p>Only the existing hand-tool reference site is connected to the ForgeBase backend.</p>
      </footer>
    </main>
  );
}
