"use client";

import Link from "next/link";
import { trackCTAClick } from "@/lib/analytics";
import { Button } from "@/components/ui/button";

type Props = {
  productId: string;
  productName: string;
  categorySlug: string;
  categoryName: string;
};

export function ProductCTAButtons({ productId, productName, categorySlug, categoryName }: Props) {
  const encodedProductName = encodeURIComponent(productName);

  return (
    <div className="mt-8 flex flex-wrap gap-3">
      <Button asChild size="lg">
        <Link
          href={`/request-quote?product_id=${productId}`}
          onClick={() => trackCTAClick("Request a Quote", `/request-quote?product_id=${productId}`)}
        >
          Request a Quote
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
