"use client";

import { Link } from "@/i18n/navigation";
import { ArrowRight, ChevronRight } from "lucide-react";
import { siteConfig } from "@/lib/siteConfig";

type HeroProps = {
  eyebrow: string;
  titleLine1: string;
  titleLine2: string;
  description: string;
  primaryCta: string;
  secondaryCta: string;
  heroImage?: string;
  stats?: Array<{ value: string; label: string }>;
};

/**
 * Industrial hero: split-layout, left-aligned, diagonal clip, safety-stripe accent.
 * Cobalt hero = centered text, gradient overlay, rounded CTA, grid pattern.
 * Industrial  = left text, right image, skewed divider, angular CTA, bold uppercase.
 */
export function IndustrialHero({
  eyebrow,
  titleLine1,
  titleLine2,
  description,
  primaryCta,
  secondaryCta,
  heroImage,
  stats,
}: HeroProps) {
  return (
    <>
      <section className="relative overflow-hidden bg-gray-950 text-white">
        {/* Safety-stripe diagonal accent */}
        <div
          className="pointer-events-none absolute inset-0 opacity-[0.03]"
          style={{
            backgroundImage:
              "repeating-linear-gradient(135deg, transparent, transparent 30px, white 30px, white 32px)",
          }}
        />

        <div className="relative mx-auto grid max-w-7xl lg:grid-cols-2">
          {/* Left: text content */}
          <div className="flex flex-col justify-center px-6 py-20 sm:px-10 sm:py-28 lg:py-32">
            {/* Eyebrow — angular tag, not rounded pill */}
            <span className="mb-5 inline-flex w-fit items-center gap-2 bg-primary/20 px-3 py-1 text-[11px] font-black uppercase tracking-[0.15em] text-primary">
              <span className="h-2 w-2 bg-primary" />
              {eyebrow}
            </span>

            <h1 className="text-4xl font-black uppercase leading-[1.05] tracking-tight sm:text-5xl lg:text-6xl">
              {titleLine1}
              <br />
              <span className="text-primary">{titleLine2}</span>
            </h1>

            <p className="mt-5 max-w-lg text-base leading-relaxed text-gray-400">
              {description}
            </p>

            <div className="mt-9 flex flex-wrap gap-4">
              {/* Primary: angular, skewed, amber */}
              <Link
                href="/rfq"
                className="group flex items-center gap-2 bg-primary px-7 py-3 text-sm font-black uppercase tracking-wider text-primary-foreground skew-x-[-3deg] hover:brightness-110 transition-all"
              >
                <span className="skew-x-[3deg]">{primaryCta}</span>
                <ArrowRight className="h-4 w-4 skew-x-[3deg] transition-transform group-hover:translate-x-1" />
              </Link>
              {/* Secondary: outlined angular */}
              <Link
                href="/products"
                className="flex items-center gap-2 border-2 border-gray-600 px-7 py-3 text-sm font-bold uppercase tracking-wider text-white skew-x-[-3deg] hover:border-gray-400 transition-colors"
              >
                <span className="skew-x-[3deg]">{secondaryCta}</span>
                <ChevronRight className="h-4 w-4 skew-x-[3deg]" />
              </Link>
            </div>
          </div>

          {/* Right: image / visual block */}
          <div className="relative hidden lg:block">
            {/* Diagonal clip divider */}
            <div className="absolute inset-y-0 left-0 w-24 bg-gray-950" style={{ clipPath: "polygon(0 0, 100% 0, 0 100%)" }} />
            {heroImage ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={heroImage}
                alt=""
                className="h-full w-full object-cover"
              />
            ) : (
              <div className="flex h-full items-center justify-center bg-gray-900">
                {/* Geometric placeholder */}
                <div className="relative">
                  <div className="h-48 w-48 border-4 border-primary/30 skew-x-[-6deg]" />
                  <div className="absolute inset-4 bg-primary/10 skew-x-[-6deg]" />
                  <div className="absolute inset-0 flex items-center justify-center">
                    <span className="text-5xl font-black text-primary/40">{siteConfig.logoMark}</span>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </section>

      {/* ── Stats strip — dark with amber numbers (cobalt: white bg, blue numbers) ── */}
      {stats && stats.length > 0 && (
        <section className="border-y border-gray-800 bg-gray-900">
          <div className="mx-auto max-w-7xl px-6 py-8">
            <div className="grid grid-cols-2 gap-6 sm:grid-cols-4">
              {stats.map((s) => (
                <div key={s.label} className="flex flex-col">
                  <span className="text-3xl font-black text-primary">{s.value}</span>
                  <span className="mt-1 text-xs font-bold uppercase tracking-wider text-gray-500">
                    {s.label}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </section>
      )}
    </>
  );
}
