"use client";

import { useMemo, useState } from "react";
import { cn } from "@/lib/utils";

type GalleryItem = {
  url: string;
  alt?: string | null;
};

type Props = {
  productName: string;
  mainImage?: string | null;
  mainAlt?: string | null;
  gallery?: Array<{ public_url: string; alt_text?: string | null }>;
  industrial?: boolean;
};

export function ProductImageGallery({ productName, mainImage, mainAlt, gallery = [], industrial }: Props) {
  const images = useMemo<GalleryItem[]>(() => {
    const items: GalleryItem[] = [];
    const seen = new Set<string>();
    const push = (url?: string | null, alt?: string | null) => {
      if (!url || seen.has(url)) return;
      seen.add(url);
      items.push({ url, alt });
    };
    push(mainImage, mainAlt);
    gallery.forEach((item) => push(item.public_url, item.alt_text));
    return items;
  }, [gallery, mainAlt, mainImage]);

  const [active, setActive] = useState(0);
  const current = images[Math.min(active, Math.max(images.length - 1, 0))];

  return (
    <div>
      <div className={cn(
        "overflow-hidden bg-gray-100 aspect-square max-h-96 lg:max-h-full",
        industrial ? "border border-gray-300" : "rounded-2xl",
      )}>
        {current ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={current.url} alt={current.alt || productName} className="h-full w-full object-cover" />
        ) : (
          <div className="flex h-full items-center justify-center text-gray-300">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-24 w-24" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
          </div>
        )}
      </div>
      {images.length > 1 && (
        <div className="mt-3 flex flex-wrap gap-2">
          {images.map((item, index) => (
            <button
              key={item.url}
              type="button"
              onClick={() => setActive(index)}
              className={cn(
                "h-16 w-16 overflow-hidden border bg-white",
                industrial ? "" : "rounded-lg",
                index === active ? "border-primary ring-2 ring-primary/30" : "border-gray-200",
              )}
              aria-label={`${productName} image ${index + 1}`}
            >
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={item.url} alt="" className="h-full w-full object-cover" />
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
