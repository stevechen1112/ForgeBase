import Link from "next/link";
import { ContactForm } from "@/components/forms/ContactForm";
import { StructuredData } from "@/components/seo/StructuredData";
import { PageViewTracker } from "@/components/tracking/PageViewTracker";
import { pageBodyLooksLikeHtml, parsePageBlocks, parseStructuredData, type FlexiblePageBlock } from "@/lib/page-content";
import type { Page } from "@/types/content";

type Props = {
  page: Page;
};

function SmartLink({ href, label, secondary = false }: { href: string; label: string; secondary?: boolean }) {
  const className = secondary
    ? "inline-flex items-center justify-center rounded-xl border border-white/20 bg-white/10 px-5 py-3 text-sm font-semibold text-white hover:bg-white/20 transition-colors"
    : "inline-flex items-center justify-center rounded-xl bg-blue-700 px-5 py-3 text-sm font-semibold text-white hover:bg-blue-800 transition-colors";

  if (/^https?:\/\//.test(href) || href.startsWith("mailto:") || href.startsWith("tel:")) {
    return <a href={href} className={className}>{label}</a>;
  }

  return <Link href={href} className={className}>{label}</Link>;
}

function SectionHeading({ eyebrow, title, description, light = false }: { eyebrow?: string; title?: string; description?: string; light?: boolean }) {
  if (!eyebrow && !title && !description) {
    return null;
  }

  return (
    <div className="mx-auto max-w-3xl text-center">
      {eyebrow ? (
        <span className={light ? "text-xs font-semibold uppercase tracking-widest text-blue-200" : "text-xs font-semibold uppercase tracking-widest text-blue-600"}>
          {eyebrow}
        </span>
      ) : null}
      {title ? <h2 className={light ? "mt-2 text-3xl font-bold text-white" : "mt-2 text-3xl font-bold text-gray-900"}>{title}</h2> : null}
      {description ? <p className={light ? "mt-3 text-base text-blue-100" : "mt-3 text-base text-gray-500"}>{description}</p> : null}
    </div>
  );
}

function renderBlock(block: FlexiblePageBlock, index: number) {
  switch (block.type) {
    case "hero": {
      const align = block.align === "left" ? "items-start text-left" : "items-center text-center";
      return (
        <section key={`hero-${index}`} className="relative overflow-hidden bg-blue-950 text-white">
          {block.backgroundImageUrl ? (
            <div className="absolute inset-0 bg-cover bg-center" style={{ backgroundImage: `url(${block.backgroundImageUrl})` }} />
          ) : null}
          <div className="absolute inset-0 bg-gradient-to-r from-slate-950/90 via-blue-950/80 to-blue-900/60" />
          <div className="relative mx-auto max-w-6xl px-6 py-24 sm:py-32">
            <div className={`flex flex-col ${align}`}>
              {block.eyebrow ? <span className="mb-5 inline-flex rounded-full border border-blue-400/30 bg-blue-800/40 px-4 py-1.5 text-xs font-semibold uppercase tracking-widest text-blue-200">{block.eyebrow}</span> : null}
              {block.title ? <h1 className="max-w-4xl text-4xl font-extrabold leading-tight tracking-tight sm:text-5xl lg:text-6xl">{block.title}</h1> : null}
              {block.description ? <p className="mt-5 max-w-3xl text-lg leading-relaxed text-blue-100">{block.description}</p> : null}
              {(block.primaryCta || block.secondaryCta) ? (
                <div className="mt-9 flex flex-col gap-4 sm:flex-row">
                  {block.primaryCta ? <SmartLink href={block.primaryCta.href} label={block.primaryCta.label} /> : null}
                  {block.secondaryCta ? <SmartLink href={block.secondaryCta.href} label={block.secondaryCta.label} secondary /> : null}
                </div>
              ) : null}
            </div>
          </div>
        </section>
      );
    }
    case "rich-text": {
      return (
        <section key={`rich-${index}`} className="bg-white py-20">
          <div className="mx-auto max-w-4xl px-6">
            <SectionHeading eyebrow={block.eyebrow} title={block.title} />
            <div className="mt-8 rounded-2xl border border-gray-200 bg-white p-8 shadow-sm">
              {pageBodyLooksLikeHtml(block.content) ? (
                <div className="prose prose-gray max-w-none" dangerouslySetInnerHTML={{ __html: block.content }} />
              ) : (
                <div className="prose prose-gray max-w-none whitespace-pre-line text-gray-700">{block.content}</div>
              )}
            </div>
          </div>
        </section>
      );
    }
    case "feature-grid": {
      const columnClass = block.columns === 4 ? "lg:grid-cols-4" : block.columns === 2 ? "lg:grid-cols-2" : "lg:grid-cols-3";
      return (
        <section key={`features-${index}`} className="bg-gray-50 py-20">
          <div className="mx-auto max-w-6xl px-6">
            <SectionHeading eyebrow={block.eyebrow} title={block.title} description={block.description} />
            <div className={`mt-12 grid gap-6 sm:grid-cols-2 ${columnClass}`}>
              {block.items.map((item, itemIndex) => (
                <div key={`${item.title ?? "item"}-${itemIndex}`} className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
                  {item.title ? <h3 className="text-base font-semibold text-gray-900">{item.title}</h3> : null}
                  {item.description ? <p className="mt-2 text-sm leading-relaxed text-gray-500">{item.description}</p> : null}
                </div>
              ))}
            </div>
          </div>
        </section>
      );
    }
    case "stats": {
      return (
        <section key={`stats-${index}`} className="border-y border-gray-100 bg-white py-10">
          <div className="mx-auto max-w-6xl px-6">
            <SectionHeading eyebrow={block.eyebrow} title={block.title} />
            <div className="mt-8 grid grid-cols-2 gap-6 sm:grid-cols-4">
              {block.items.map((item) => (
                <div key={`${item.value}-${item.label}`} className="flex flex-col items-center text-center">
                  <span className="text-3xl font-extrabold text-blue-700">{item.value}</span>
                  <span className="mt-1 text-sm text-gray-500">{item.label}</span>
                </div>
              ))}
            </div>
          </div>
        </section>
      );
    }
    case "checklist": {
      return (
        <section key={`checklist-${index}`} className="bg-white py-20">
          <div className="mx-auto max-w-5xl px-6">
            <SectionHeading eyebrow={block.eyebrow} title={block.title} description={block.description} />
            <div className="mt-10 grid gap-3 sm:grid-cols-2">
              {block.items.map((item) => (
                <div key={item} className="flex items-start gap-3 rounded-xl border border-gray-200 bg-gray-50 p-4">
                  <div className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-blue-100 text-blue-700">✓</div>
                  <p className="text-sm text-gray-700">{item}</p>
                </div>
              ))}
            </div>
          </div>
        </section>
      );
    }
    case "cta": {
      return (
        <section key={`cta-${index}`} className="bg-blue-950 py-20 text-white">
          <div className="mx-auto max-w-5xl px-6 text-center">
            <SectionHeading eyebrow={block.eyebrow} title={block.title} description={block.description} light />
            <div className="mt-8 flex flex-col items-center justify-center gap-4 sm:flex-row">
              <SmartLink href={block.primaryCta.href} label={block.primaryCta.label} />
              {block.secondaryCta ? <SmartLink href={block.secondaryCta.href} label={block.secondaryCta.label} secondary /> : null}
            </div>
          </div>
        </section>
      );
    }
    case "contact-form": {
      return (
        <section key={`contact-form-${index}`} className="bg-white py-20">
          <div className="mx-auto max-w-4xl px-6">
            <SectionHeading eyebrow={block.eyebrow} title={block.title} description={block.description} />
            <div className="mt-10 rounded-xl border border-gray-200 bg-white p-8 shadow-sm">
              <ContactForm />
            </div>
          </div>
        </section>
      );
    }
    case "contact-cards": {
      return (
        <section key={`contact-cards-${index}`} className="bg-gray-50 py-20">
          <div className="mx-auto max-w-6xl px-6">
            <SectionHeading eyebrow={block.eyebrow} title={block.title} />
            <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {block.items.map((item, itemIndex) => (
                <div key={`${item.title ?? "card"}-${itemIndex}`} className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
                  {item.title ? <h3 className="text-sm font-semibold text-blue-700">{item.title}</h3> : null}
                  <div className="mt-2 space-y-1 text-sm text-gray-600">
                    {item.description ? <p>{item.description}</p> : null}
                    {item.lines?.map((line) => <p key={line}>{line}</p>)}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>
      );
    }
    case "split": {
      return (
        <section key={`split-${index}`} className="bg-white py-20">
          <div className="mx-auto grid max-w-6xl gap-10 px-6 lg:grid-cols-2 lg:items-center">
            <div>
              <SectionHeading eyebrow={block.eyebrow} title={block.title} />
              {block.content ? (
                pageBodyLooksLikeHtml(block.content) ? (
                  <div className="prose prose-gray mt-6 max-w-none" dangerouslySetInnerHTML={{ __html: block.content }} />
                ) : (
                  <div className="mt-6 whitespace-pre-line text-gray-700">{block.content}</div>
                )
              ) : null}
              {block.primaryCta ? <div className="mt-8"><SmartLink href={block.primaryCta.href} label={block.primaryCta.label} /></div> : null}
            </div>
            <div>
              {block.imageUrl ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={block.imageUrl} alt={block.imageAlt ?? block.title ?? "page image"} className="aspect-video w-full rounded-2xl border border-gray-200 object-cover shadow-sm" />
              ) : null}
            </div>
          </div>
        </section>
      );
    }
    default:
      return null;
  }
}

export function FlexiblePageRenderer({ page }: Props) {
  const blocks = parsePageBlocks(page);
  const structuredData = parseStructuredData(page);

  return (
    <>
      <PageViewTracker pageType={page.page_type || "page"} pageId={page.id} />
      {structuredData ? <StructuredData data={structuredData} /> : null}

      {blocks?.length ? (
        blocks.map((block, index) => renderBlock(block, index))
      ) : (
        <>
          <section className="relative overflow-hidden bg-blue-950 text-white">
            {page.hero_image_url ? (
              <div className="absolute inset-0 bg-cover bg-center" style={{ backgroundImage: `url(${page.hero_image_url})` }} />
            ) : null}
            <div className="absolute inset-0 bg-gradient-to-r from-slate-950/90 via-blue-950/80 to-blue-900/60" />
            <div className="relative mx-auto max-w-6xl px-6 py-24 sm:py-32 text-center">
              <h1 className="text-4xl font-extrabold leading-tight tracking-tight sm:text-5xl lg:text-6xl">{page.title}</h1>
              {page.subtitle ? <p className="mx-auto mt-5 max-w-3xl text-lg leading-relaxed text-blue-100">{page.subtitle}</p> : null}
            </div>
          </section>

          {page.body ? (
            <section className="bg-white py-20">
              <div className="mx-auto max-w-4xl px-6">
                <div className="rounded-2xl border border-gray-200 bg-white p-8 shadow-sm">
                  {pageBodyLooksLikeHtml(page.body) ? (
                    <div className="prose prose-gray max-w-none" dangerouslySetInnerHTML={{ __html: page.body }} />
                  ) : (
                    <div className="prose prose-gray max-w-none whitespace-pre-line text-gray-700">{page.body}</div>
                  )}
                </div>
              </div>
            </section>
          ) : null}
        </>
      )}
    </>
  );
}