"use client";
/**
 * PageViewTracker — 1b.1.4
 *
 * A zero-UI client component that fires a tracking event when mounted.
 * Drop this at the bottom of any Server Component page to capture page views.
 *
 * Usage:
 *   import { PageViewTracker } from "@/components/tracking/PageViewTracker";
 *
 *   // In a Server Component:
 *   export default async function ProductPage({ params }) {
 *     const product = await getProduct(params.slug);
 *     return (
 *       <>
 *         <ProductDetail product={product} />
 *         <PageViewTracker pageType="product" pageId={product.id} />
 *       </>
 *     );
 *   }
 */
import { useEffect, useRef } from "react";
import { track, type EventName } from "@/lib/analytics";

interface Props {
  pageType: string;
  /** Backend UUID of the page entity (product.id, application.id, etc.) */
  pageId?: string;
  /** Override event name — defaults to the appropriate page-type event */
  eventName?: EventName;
  /** Any extra properties to send with the event */
  extra?: Record<string, unknown>;
}

const PAGE_TYPE_TO_EVENT: Record<string, EventName> = {
  product: "product_view",
  category: "category_view",
  application: "application_view",
  comparison: "comparison_view",
  certification: "certification_view",
  faq: "page_view",
  contact: "page_view",
  rfq: "page_view",
  home: "page_view",
};

export function PageViewTracker({ pageType, pageId, eventName, extra = {} }: Props) {
  const fired = useRef(false);

  useEffect(() => {
    if (fired.current) return;
    fired.current = true;

    const name: EventName = eventName ?? PAGE_TYPE_TO_EVENT[pageType] ?? "page_view";
    track(name, { page_type: pageType, page_id: pageId, ...extra });
  }, []);  // eslint-disable-line react-hooks/exhaustive-deps — intentionally fires once

  return null; // renders nothing
}
