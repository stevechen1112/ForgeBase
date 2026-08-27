"use client";

import { useEffect, useState } from "react";
import { useLocale } from "next-intl";
import { Link } from "@/i18n/navigation";
import { track, trackCTAClick, getAnalyticsVisitorId } from "@/lib/analytics";
import { Button } from "@/components/ui/button";
import { siteConfig } from "@/lib/siteConfig";
import { withTenantHeaders } from "@/lib/tenant";

type DynamicCTA = {
  cta: { id?: string; label?: string; action_type?: string; description?: string } | null;
  variant: string;
  personalization: { headline_prefix?: string; cta_label_override?: string };
  fallback_used: boolean;
  decision_id?: string;
};

type Props = {
  productId: string;
  productName: string;
  categorySlug: string;
  categoryName: string;
  industrial?: boolean;
};

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

export function ProductCTAButtons({ productId, productName, categorySlug, categoryName, industrial }: Props) {
  const encodedProductName = encodeURIComponent(productName);
  const [dynamic, setDynamic] = useState<DynamicCTA | null>(null);
  const locale = useLocale();
  const isIndustrial = industrial ?? siteConfig.layout === "industrial";

  useEffect(() => {
    const params = new URLSearchParams({
      page_type: "product",
      entity_id: productId,
      entity_name: productName,
      locale,
    });
    const vid = getAnalyticsVisitorId();
    if (vid) params.set("visitor_id", vid);
    fetch(`${API_BASE}/api/v1/content/dynamic-cta?${params}`, {
      headers: withTenantHeaders(),
    })
      .then((r) => r.ok ? r.json() : null)
      .then((data: DynamicCTA | null) => {
        if (!data) return;
        setDynamic(data);
        if (data.cta?.id) {
          void track("cta_impression", {
            cta_id: data.cta.id,
            decision_id: data.decision_id,
            page_type: "product",
            page_id: productId,
          });
        }
      })
      .catch(() => {});
  }, [locale, productId, productName]);

  // Determine primary CTA label based on dynamic result
  const zh = locale.toLowerCase().startsWith("zh");
  const primaryLabel = dynamic?.personalization?.cta_label_override || dynamic?.cta?.label || (zh ? "立即詢價" : "Request a Quote");
  const contactLabel = zh ? "聯絡我們" : "Contact Us";
  const backLabel = zh ? `返回${categoryName}` : `Back to ${categoryName}`;
  const isUrgent = dynamic?.variant === "urgent";

  if (isIndustrial) {
    return (
      <div className="mt-8 flex flex-wrap gap-3">
        {dynamic?.personalization?.headline_prefix && (
          <p className="mb-1 w-full text-xs font-black uppercase tracking-[0.16em] text-gray-500">
            {dynamic.personalization.headline_prefix}
          </p>
        )}
        <Link
          href={`/request-quote?product_id=${productId}`}
          onClick={() => trackCTAClick(primaryLabel, `/request-quote?product_id=${productId}`)}
          className={isUrgent
            ? "flex items-center bg-red-600 px-6 py-3 text-sm font-black uppercase tracking-[0.16em] text-white skew-x-[-3deg] hover:bg-red-700"
            : "flex items-center bg-primary px-6 py-3 text-sm font-black uppercase tracking-[0.16em] text-primary-foreground skew-x-[-3deg] hover:brightness-110"}
        >
          <span className="skew-x-[3deg]">{primaryLabel}</span>
        </Link>
        <Link
          href={`/contact?ref=product&product=${encodedProductName}`}
          onClick={() => trackCTAClick(contactLabel, `/contact?ref=product&product=${encodedProductName}`)}
          className="flex items-center border-2 border-gray-300 px-6 py-3 text-sm font-bold uppercase tracking-[0.16em] text-gray-800 skew-x-[-3deg] hover:border-primary hover:text-primary"
        >
          <span className="skew-x-[3deg]">{contactLabel}</span>
        </Link>
        <Link
          href={`/products/${categorySlug}`}
          className="flex items-center border border-gray-300 px-6 py-3 text-sm font-bold uppercase tracking-[0.16em] text-gray-500 skew-x-[-3deg] hover:border-gray-500 hover:text-gray-700"
        >
          <span className="skew-x-[3deg]">{backLabel}</span>
        </Link>
      </div>
    );
  }

  return (
    <div className="mt-8 flex flex-wrap gap-3">
      {dynamic?.personalization?.headline_prefix && (
        <p className="w-full text-sm font-medium text-muted-foreground mb-1">
          {dynamic.personalization.headline_prefix}
        </p>
      )}
      <Button asChild size="lg" variant={isUrgent ? "destructive" : "default"}>
        <Link
          href={`/request-quote?product_id=${productId}`}
          onClick={() => trackCTAClick(primaryLabel, `/request-quote?product_id=${productId}`)}
        >
          {primaryLabel}
        </Link>
      </Button>
      <Button asChild variant="outline" size="lg">
        <Link
          href={`/contact?ref=product&product=${encodedProductName}`}
          onClick={() => trackCTAClick(contactLabel, `/contact?ref=product&product=${encodedProductName}`)}
        >
          {contactLabel}
        </Link>
      </Button>
      <Button asChild variant="ghost" size="lg">
        <Link href={`/products/${categorySlug}`}>
          {backLabel}
        </Link>
      </Button>
    </div>
  );
}
