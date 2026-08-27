/* eslint-disable @next/next/no-img-element -- tenant assets are resolved dynamically from the CMS manifest */
import Link from "next/link";
import {
  ArrowRight,
  Check,
  Crosshair,
  FileCheck2,
  Gauge,
  ScanLine,
} from "lucide-react";
import type {
  Application,
  Certification,
  Product,
  ProductCategory,
} from "@/types/content";
import type { SiteConfig } from "@/lib/siteConfig";
import {
  getHomeHeroImage,
  getProductImage,
  getQualityInspectionImage,
} from "@/lib/demoAssets";
import { localizedPath } from "@/lib/localizedPath";

type Copy = {
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

type Props = {
  copy: Copy;
  featuredProducts: Product[];
  categories: ProductCategory[];
  applications: Application[];
  certifications: Certification[];
  categorySlugById: Map<string, string>;
  siteConfig: SiteConfig;
  locale: string;
};

const icons = [Crosshair, Gauge, FileCheck2];

export function PrecisionHomePage({
  copy,
  featuredProducts,
  applications,
  certifications,
  categorySlugById,
  siteConfig,
  locale,
}: Props) {
  const hero = getHomeHeroImage(siteConfig);
  const quality = getQualityInspectionImage(siteConfig);
  return (
    <>
      <section className="grid min-h-[650px] bg-[#0b1013] text-white lg:grid-cols-[54%_46%]">
        <div className="flex flex-col justify-center px-6 py-20 lg:px-[max(2.5rem,calc((100vw-1440px)/2+2.5rem))]">
          <p className="mb-6 text-xs font-black uppercase tracking-[0.22em] text-lime-300">
            {copy.hero.eyebrow}
          </p>
          <h1 className="max-w-3xl text-5xl font-black uppercase leading-[0.94] tracking-[-0.04em] sm:text-6xl xl:text-7xl">
            {copy.hero.titleLine1}
            <br />
            <span className="text-lime-300">{copy.hero.titleLine2}</span>
          </h1>
          <p className="mt-7 max-w-2xl border-l border-lime-300/70 pl-5 text-base leading-7 text-gray-400">
            {copy.hero.description}
          </p>
          <div className="mt-9 flex flex-wrap gap-3">
            <Link
              href={localizedPath(locale, "/rfq")}
              className="inline-flex items-center gap-2 bg-lime-300 px-6 py-4 text-xs font-black uppercase tracking-wider text-black"
            >
              {copy.hero.primaryCta}
              <ArrowRight size={16} />
            </Link>
            <Link
              href={localizedPath(locale, "/products")}
              className="border border-white/25 px-6 py-4 text-xs font-black uppercase tracking-wider"
            >
              {copy.hero.secondaryCta}
            </Link>
          </div>
          <div className="mt-12 grid max-w-2xl grid-cols-3 border-y border-white/10 py-5">
            {copy.stats.slice(0, 3).map((s) => (
              <div
                key={s.label}
                className="border-r border-white/10 px-3 first:pl-0 last:border-0"
              >
                <strong className="block text-xl text-lime-300">
                  {s.value}
                </strong>
                <span className="text-[10px] uppercase tracking-wider text-gray-500">
                  {s.label}
                </span>
              </div>
            ))}
          </div>
        </div>
        <div className="relative min-h-[430px] overflow-hidden border-l border-white/10">
          {hero && (
            <img
              src={hero}
              alt="Fictional CNC machining demonstration facility"
              className="absolute inset-0 h-full w-full object-cover"
            />
          )}
          <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/5 to-black/20" />
          <div className="absolute bottom-8 left-8 flex items-center gap-3 border border-white/30 bg-black/70 px-4 py-3 text-xs font-bold tracking-wider">
            <ScanLine className="text-lime-300" size={18} /> DEMO-M01 / REV.B
          </div>
        </div>
      </section>
      <section className="border-y border-gray-300 bg-white py-16">
        <div className="mx-auto max-w-[1440px] px-6 lg:px-10">
          <p className="text-xs font-black uppercase tracking-[0.2em] text-gray-500">
            01 / {copy.why.eyebrow}
          </p>
          <div className="mt-4 grid gap-8 lg:grid-cols-[.9fr_1.4fr]">
            <div>
              <h2 className="text-4xl font-black uppercase tracking-tight text-gray-950">
                {copy.why.title}
              </h2>
              <p className="mt-4 max-w-lg leading-7 text-gray-600">
                {copy.why.description}
              </p>
            </div>
            <div className="grid gap-px bg-gray-300 sm:grid-cols-3">
              {copy.why.items.slice(0, 3).map((item, index) => {
                const Icon = icons[index];
                return (
                  <article key={item.title} className="bg-gray-50 p-7">
                    <span className="text-xs font-black text-gray-400">
                      0{index + 1}
                    </span>
                    <Icon className="mt-7 text-lime-600" />
                    <h3 className="mt-5 text-base font-black uppercase">
                      {item.title}
                    </h3>
                    <p className="mt-3 text-sm leading-6 text-gray-600">
                      {item.desc}
                    </p>
                  </article>
                );
              })}
            </div>
          </div>
        </div>
      </section>
      {featuredProducts.length > 0 && (
        <section className="bg-[#111719] py-16 text-white">
          <div className="mx-auto max-w-[1440px] px-6 lg:px-10">
            <p className="text-xs font-black uppercase tracking-[0.2em] text-lime-300">
              02 / {copy.featured.eyebrow}
            </p>
            <h2 className="mt-4 text-4xl font-black uppercase">
              {copy.featured.title}
            </h2>
            <p className="mt-3 max-w-2xl text-gray-400">
              {copy.featured.description}
            </p>
            <div className="mt-10 divide-y divide-white/10 border-y border-white/10">
            {featuredProducts.map((product) => {
                const categorySlug = categorySlugById.get(product.category_id);
                const img = getProductImage(product, categorySlug, siteConfig);
                return (
                  <Link
                    key={product.id}
                    href={localizedPath(
                      locale,
                      categorySlug
                        ? `/products/${categorySlug}/${product.slug}`
                        : "/products",
                    )}
                    className="group grid items-center gap-5 py-6 md:grid-cols-[90px_1.1fr_1.5fr_auto]"
                  >
                    <div className="h-16 bg-white/5">
                      {img && (
                        <img
                          src={img}
                          alt={product.image_alt || product.product_name}
                          className="h-full w-full object-cover"
                        />
                      )}
                    </div>
                    <div>
                      <small className="font-mono text-lime-300">
                        {product.model_number}
                      </small>
                      <h3 className="mt-1 font-black uppercase">
                        {product.product_name}
                      </h3>
                    </div>
                    <p className="text-sm text-gray-500">
                      {product.short_description}
                    </p>
                    <ArrowRight className="text-gray-600 group-hover:text-lime-300" />
                  </Link>
                );
              })}
            </div>
          </div>
        </section>
      )}
      <section className="grid bg-gray-100 lg:grid-cols-2">
        <div className="relative min-h-[420px]">
          {quality && (
            <img
              src={quality}
              alt="Fictional CMM inspection demonstration"
              className="absolute inset-0 h-full w-full object-cover"
            />
          )}
          <div className="absolute inset-0 bg-black/35" />
          <span className="absolute left-6 top-6 bg-black/80 px-4 py-2 text-[10px] font-black uppercase tracking-wider text-lime-300">
            Demo / Not certified
          </span>
        </div>
        <div className="flex flex-col justify-center px-7 py-16 lg:px-16">
          <p className="text-xs font-black uppercase tracking-[0.2em] text-lime-700">
            03 / {copy.certifications.eyebrow}
          </p>
          <h2 className="mt-4 text-4xl font-black uppercase">
            {copy.certifications.title}
          </h2>
          <p className="mt-4 max-w-xl leading-7 text-gray-600">
            {copy.certifications.description}
          </p>
          <ul className="mt-8 space-y-4">
            {certifications.slice(0, 4).map((cert) => (
              <li
                key={cert.id}
                className="flex gap-3 border-b border-gray-300 pb-4"
              >
                <Check className="shrink-0 text-lime-700" />
                <span>
                  <strong className="block uppercase">{cert.cert_name}</strong>
                  <small className="text-gray-500">{cert.description}</small>
                </span>
              </li>
            ))}
          </ul>
        </div>
      </section>
      {applications.length > 0 && (
        <section className="bg-white py-16">
          <div className="mx-auto max-w-[1440px] px-6 lg:px-10">
            <p className="text-xs font-black uppercase tracking-[0.2em] text-gray-500">
              04 / {copy.applications.eyebrow}
            </p>
            <h2 className="mt-4 text-4xl font-black uppercase">
              {copy.applications.title}
            </h2>
            <div className="mt-9 grid gap-px bg-gray-300 md:grid-cols-3">
              {applications.slice(0, 3).map((app) => (
                <Link
                  key={app.id}
                  href={localizedPath(locale, `/applications/${app.slug}`)}
                  className="bg-gray-50 p-7 hover:bg-lime-50"
                >
                  <small className="font-mono text-gray-500">
                    {app.industry}
                  </small>
                  <h3 className="mt-5 text-xl font-black uppercase">
                    {app.application_name}
                  </h3>
                  <p className="mt-3 text-sm leading-6 text-gray-600">
                    {app.description}
                  </p>
                  <ArrowRight className="mt-6" />
                </Link>
              ))}
            </div>
          </div>
        </section>
      )}
      <section className="bg-lime-300 px-6 py-16 text-black">
        <div className="mx-auto flex max-w-[1440px] flex-col justify-between gap-8 lg:flex-row lg:items-center">
          <div>
            <h2 className="max-w-3xl text-4xl font-black uppercase tracking-tight">
              {copy.finalCta.title}
            </h2>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-black/70">
              {copy.finalCta.description}
            </p>
          </div>
          <Link
            href={localizedPath(locale, "/rfq")}
            className="inline-flex h-fit items-center gap-3 bg-black px-7 py-4 text-xs font-black uppercase tracking-wider text-white"
          >
            {copy.finalCta.primaryCta}
            <ArrowRight />
          </Link>
        </div>
      </section>
    </>
  );
}
