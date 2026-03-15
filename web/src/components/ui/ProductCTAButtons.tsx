"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { trackCTAClick, getVisitorId } from "@/lib/analytics";
import { Button } from "@/components/ui/button";

type DynamicCTA = {
  cta: { label?: string; action_type?: string; description?: string } | null;
  variant: string;
  personalization: { headline_prefix?: string; cta_label_override?: string };
  fallback_used: boolean;
};

type Props = {
  productId: string;
  productName: string;
  categorySlug: string;
  categoryName: string;
};

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

export function ProductCTAButtons({ productId, productName, categorySlug, categoryName }: Props) {
  const encodedProductName = encodeURIComponent(productName);
  const [dynamic, setDynamic] = useState<DynamicCTA | null>(null);

  useEffect(() => {
    const vid = getVisitorId();
    const params = new URLSearchParams({
      visitor_id: vid,
      page_type: "product",
      entity_id: productId,
      entity_name: productName,
    });
    fetch(`${API_BASE}/api/v1/content/dynamic-cta?${params}`)
      .then((r) => r.ok ? r.json() : null)
      .then((data) => { if (data) setDynamic(data); })
      .catch(() => {});
  }, [productId, productName]);

  // Determine primary CTA label based on dynamic result
  const primaryLabel = dynamic?.personalization?.cta_label_override || "Request a Quote";
  const isUrgent = dynamic?.variant === "urgent";

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
          onClick={() => trackCTAClick("Contact Us", `/contact?ref=product&product=${encodedProductName}`)}
        >
          Contact Us
        </Link>
      </Button>
      <Button asChild variant="ghost" size="lg">
        <Link href={`/products/${categorySlug}`}>
          ← Back to {categoryName}
        </Link>
      </Button>
    </div>
  );
}
