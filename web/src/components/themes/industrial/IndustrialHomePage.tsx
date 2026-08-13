import Link from "next/link";
import { ApplicationCard } from "@/components/ui/ApplicationCard";
import { CertificationBadge } from "@/components/ui/CertificationBadge";
import { IndustrialHero } from "@/components/themes/industrial/IndustrialHero";
import { getCategoryCardImage, getHomeHeroImage, getProductImage } from "@/lib/demoAssets";
import { ArrowRight, ChevronRight } from "lucide-react";
import type { Product, ProductCategory, Application, Certification } from "@/types/content";
import type { SiteConfig } from "@/lib/siteConfig";
import { localizedPath } from "@/lib/localizedPath";

/**
 * Industrial homepage: angular, left-aligned, dark sections, bold typography.
 *
 * Contrast with cobalt classic (centered, rounded, light bg, blue accents):
 *  - Hero:        split-layout vs centered          ✓
 *  - Stats:       dark bg + amber vs white + blue    ✓
 *  - Products:    horizontal cards vs vertical grid   ✓
 *  - Categories:  list-style vs icon grid            ✓
 *  - Why Us:      numbered list vs icon cards        ✓
 *  - OEM:         timeline vs numbered cards         ✓
 *  - CTA:         diagonal-stripe vs blue banner     ✓
 */

type SectionHeadingProps = {
  eyebrow: string;
  title: string;
  description?: string;
};

/** Left-aligned heading with thick primary bar (cobalt = centered, no bar) */
function SectionHeading({ eyebrow, title, description }: SectionHeadingProps) {
  return (
    <div className="mb-10">
      <div className="flex items-center gap-3">
        <div className="h-6 w-1.5 bg-primary" />
        <span className="text-[10px] font-black uppercase tracking-[0.2em] text-primary">
          {eyebrow}
        </span>
      </div>
      <h2 className="mt-2 text-2xl font-black uppercase tracking-tight text-gray-900 sm:text-3xl">
        {title}
      </h2>
      {description && (
        <p className="mt-2 max-w-xl text-sm leading-relaxed text-gray-500">
          {description}
        </p>
      )}
    </div>
  );
}

type IndustrialHomePageProps = {
  copy: {
    hero: {
      eyebrow: string;
      titleLine1: string;
      titleLine2: string;
      description: string;
      primaryCta: string;
      secondaryCta: string;
    };
    stats: Array<{ value: string; label: string }>;
    featured: {
      eyebrow: string;
      title: string;
      description: string;
      cardCta: string;
      sectionCta: string;
    };
    catalogue: {
      eyebrow: string;
      title: string;
      description: string;
      sectionCta: string;
    };
    why: {
      eyebrow: string;
      title: string;
      description: string;
      items: Array<{ title: string; desc: string }>;
    };
    applications: {
      eyebrow: string;
      title: string;
      description: string;
      sectionCta: string;
    };
    oem: {
      eyebrow: string;
      title: string;
      description: string;
      steps: Array<{ title: string; desc: string }>;
    };
    certifications: {
      eyebrow: string;
      title: string;
      description: string;
      sectionCta: string;
    };
    finalCta: {
      title: string;
      description: string;
      primaryCta: string;
      secondaryCta: string;
      note: string;
    };
  };
  featuredProducts: Product[];
  categories: ProductCategory[];
  applications: Application[];
  certifications: Certification[];
  categorySlugById: Map<string, string>;
  siteConfig: SiteConfig;
  locale?: string;
};

export function IndustrialHomePage({
  copy,
  featuredProducts,
  categories,
  applications,
  certifications,
  categorySlugById,
  siteConfig,
  locale = "en",
}: IndustrialHomePageProps) {
  return (
    <>
      {/* ── Hero (split-layout, left-aligned) ── */}
      <IndustrialHero
        eyebrow={copy.hero.eyebrow}
        titleLine1={copy.hero.titleLine1}
        titleLine2={copy.hero.titleLine2}
        description={copy.hero.description}
        primaryCta={copy.hero.primaryCta}
        secondaryCta={copy.hero.secondaryCta}
        heroImage={getHomeHeroImage(siteConfig) ?? undefined}
        stats={copy.stats}
        locale={locale}
      />

      {/* ── Featured Products — horizontal cards (cobalt: vertical 4-col grid) ── */}
      {featuredProducts.length > 0 && (
        <section className="bg-white py-16">
          <div className="mx-auto max-w-7xl px-6">
            <SectionHeading
              eyebrow={copy.featured.eyebrow}
              title={copy.featured.title}
              description={copy.featured.description}
            />

            <div className="space-y-4">
              {featuredProducts.slice(0, 4).map((product) => {
                const catSlug = categorySlugById.get(product.category_id);
                const href = localizedPath(locale, catSlug ? `/products/${catSlug}/${product.slug}` : "/products");
                const imgSrc = getProductImage(product, catSlug, siteConfig);
                return (
                  <Link
                    key={product.id}
                    href={href}
                    className="group flex items-stretch border border-gray-200 bg-white hover:border-primary/40 transition-colors"
                  >
                    {/* Thumbnail */}
                    <div className="hidden w-40 flex-shrink-0 overflow-hidden bg-gray-100 sm:block">
                      {imgSrc ? (
                        // eslint-disable-next-line @next/next/no-img-element
                        <img
                          src={imgSrc}
                          alt={product.product_name}
                          className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
                        />
                      ) : (
                        <div className="flex h-full items-center justify-center text-3xl text-gray-300">
                          ⬡
                        </div>
                      )}
                    </div>
                    {/* Content */}
                    <div className="flex flex-1 items-center justify-between px-5 py-4">
                      <div>
                        <h3 className="text-sm font-bold uppercase tracking-wide text-gray-900 group-hover:text-primary transition-colors">
                          {product.product_name}
                        </h3>
                        {product.model_number && (
                          <p className="mt-0.5 text-xs text-gray-400">{product.model_number}</p>
                        )}
                        {product.short_description && (
                          <p className="mt-1 line-clamp-1 max-w-md text-xs text-gray-500">
                            {product.short_description}
                          </p>
                        )}
                      </div>
                      <ArrowRight className="h-4 w-4 flex-shrink-0 text-gray-300 transition-transform group-hover:translate-x-1 group-hover:text-primary" />
                    </div>
                  </Link>
                );
              })}
            </div>

            <div className="mt-8">
              <Link
                href={localizedPath(locale, "/products")}
                className="inline-flex items-center gap-2 bg-gray-900 px-6 py-2.5 text-xs font-black uppercase tracking-wider text-white skew-x-[-3deg] hover:bg-gray-700 transition-colors"
              >
                <span className="skew-x-[3deg]">{copy.featured.sectionCta}</span>
                <ArrowRight className="h-3.5 w-3.5 skew-x-[3deg]" />
              </Link>
            </div>
          </div>
        </section>
      )}

      {/* ── Categories — compact list (cobalt: icon grid cards) ── */}
      {categories.length > 0 && (
        <section className="border-y border-gray-200 bg-gray-50 py-16">
          <div className="mx-auto max-w-7xl px-6">
            <SectionHeading
              eyebrow={copy.catalogue.eyebrow}
              title={copy.catalogue.title}
              description={copy.catalogue.description}
            />

            <div className="grid gap-px bg-gray-200 sm:grid-cols-2 lg:grid-cols-4">
              {categories.map((cat) => (
                <Link
                  key={cat.id}
                  href={localizedPath(locale, `/products/${cat.slug}`)}
                  className="group flex items-center gap-4 bg-white p-5 hover:bg-primary/5 transition-colors"
                >
                  {getCategoryCardImage(cat, siteConfig) ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={getCategoryCardImage(cat, siteConfig) ?? undefined}
                      alt={cat.category_name}
                      className="h-12 w-12 flex-shrink-0 object-cover"
                    />
                  ) : (
                    <div className="flex h-12 w-12 flex-shrink-0 items-center justify-center bg-gray-100 text-lg text-gray-400">
                      ⬡
                    </div>
                  )}
                  <div>
                    <span className="text-sm font-bold text-gray-900 group-hover:text-primary transition-colors">
                      {cat.category_name}
                    </span>
                    <ChevronRight className="ml-1 inline h-3.5 w-3.5 text-gray-300 transition-transform group-hover:translate-x-1 group-hover:text-primary" />
                  </div>
                </Link>
              ))}
            </div>

            <div className="mt-8">
              <Link
                href={localizedPath(locale, "/products")}
                className="inline-flex items-center gap-1 text-xs font-black uppercase tracking-wider text-primary hover:underline"
              >
                {copy.catalogue.sectionCta}
                <ArrowRight className="h-3.5 w-3.5" />
              </Link>
            </div>
          </div>
        </section>
      )}

      {/* ── Why Choose Us — numbered rows (cobalt: 3-col icon cards) ── */}
      <section className="bg-white py-16">
        <div className="mx-auto max-w-7xl px-6">
          <SectionHeading
            eyebrow={copy.why.eyebrow}
            title={copy.why.title}
            description={copy.why.description}
          />

          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {copy.why.items.map((item, index) => (
              <div
                key={item.title}
                className="group border-l-4 border-gray-200 bg-gray-50 p-5 hover:border-primary transition-colors"
              >
                <span className="text-2xl font-black text-gray-200 group-hover:text-primary/30 transition-colors">
                  0{index + 1}
                </span>
                <h3 className="mt-2 text-sm font-bold uppercase tracking-wide text-gray-900">
                  {item.title}
                </h3>
                <p className="mt-1.5 text-xs leading-relaxed text-gray-500">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Applications ── */}
      {applications.length > 0 && (
        <section className="border-y border-gray-200 bg-gray-50 py-16">
          <div className="mx-auto max-w-7xl px-6">
            <SectionHeading
              eyebrow={copy.applications.eyebrow}
              title={copy.applications.title}
              description={copy.applications.description}
            />

            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {applications.map((app) => (
                <ApplicationCard key={app.id} application={app} siteConfig={siteConfig} locale={locale} />
              ))}
            </div>

            <div className="mt-8">
              <Link
                href={localizedPath(locale, "/applications")}
                className="inline-flex items-center gap-1 text-xs font-black uppercase tracking-wider text-primary hover:underline"
              >
                {copy.applications.sectionCta}
                <ArrowRight className="h-3.5 w-3.5" />
              </Link>
            </div>
          </div>
        </section>
      )}

      {/* ── OEM/ODM flow — vertical timeline (cobalt: numbered round-badge cards) ── */}
      <section className="bg-white py-16">
        <div className="mx-auto max-w-7xl px-6">
          <SectionHeading
            eyebrow={copy.oem.eyebrow}
            title={copy.oem.title}
            description={copy.oem.description}
          />

          <div className="relative ml-4 border-l-2 border-gray-200 pl-8">
            {copy.oem.steps.map((step, index) => (
              <div key={step.title} className="relative pb-10 last:pb-0">
                {/* Timeline dot */}
                <div className="absolute -left-[calc(2rem+5px)] flex h-10 w-10 items-center justify-center bg-primary text-sm font-black text-primary-foreground">
                  0{index + 1}
                </div>
                <h3 className="text-sm font-bold uppercase tracking-wide text-gray-900">
                  {step.title}
                </h3>
                <p className="mt-1 max-w-lg text-xs leading-relaxed text-gray-500">{step.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Certifications ── */}
      {certifications.length > 0 && (
        <section className="border-y border-gray-200 bg-gray-50 py-16">
          <div className="mx-auto max-w-7xl px-6">
            <SectionHeading
              eyebrow={copy.certifications.eyebrow}
              title={copy.certifications.title}
              description={copy.certifications.description}
            />

            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
              {certifications.map((cert) => (
                <CertificationBadge key={cert.id} certification={cert} locale={locale} />
              ))}
            </div>

            <div className="mt-8">
              <Link
                href={localizedPath(locale, "/certifications")}
                className="inline-flex items-center gap-1 text-xs font-black uppercase tracking-wider text-primary hover:underline"
              >
                {copy.certifications.sectionCta}
                <ArrowRight className="h-3.5 w-3.5" />
              </Link>
            </div>
          </div>
        </section>
      )}

      {/* ── CTA Banner — diagonal stripe (cobalt: solid blue-900 banner) ── */}
      <section className="relative overflow-hidden bg-gray-950 py-16 text-white">
        <div
          className="pointer-events-none absolute inset-0 opacity-[0.04]"
          style={{
            backgroundImage:
              "repeating-linear-gradient(135deg, transparent, transparent 30px, white 30px, white 32px)",
          }}
        />
        <div className="relative mx-auto max-w-7xl px-6">
          <div className="flex flex-col items-start gap-8 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <h2 className="text-2xl font-black uppercase tracking-tight sm:text-3xl">
                {copy.finalCta.title}
              </h2>
              <p className="mt-3 max-w-xl text-sm leading-relaxed text-gray-400">
                {copy.finalCta.description}
              </p>
            </div>

            <div className="flex flex-wrap gap-4">
              <Link
                href={localizedPath(locale, "/rfq")}
                className="flex items-center gap-2 bg-primary px-7 py-3 text-sm font-black uppercase tracking-wider text-primary-foreground skew-x-[-3deg] hover:brightness-110 transition-all"
              >
                <span className="skew-x-[3deg]">{copy.finalCta.primaryCta}</span>
                <ArrowRight className="h-4 w-4 skew-x-[3deg]" />
              </Link>
              <Link
                href={localizedPath(locale, "/contact")}
                className="flex items-center gap-2 border-2 border-gray-600 px-7 py-3 text-sm font-bold uppercase tracking-wider text-white skew-x-[-3deg] hover:border-gray-400 transition-colors"
              >
                <span className="skew-x-[3deg]">{copy.finalCta.secondaryCta}</span>
              </Link>
            </div>
          </div>
          <p className="mt-6 text-xs text-gray-600">{copy.finalCta.note}</p>
        </div>
      </section>
    </>
  );
}
