"use client";

import { useRouter, usePathname, useSearchParams } from "next/navigation";
import { useCallback, useTransition } from "react";
import { siteConfig } from "@/lib/siteConfig";

interface Props {
  placeholder?: string;
}

/**
 * 2.3.1 Faceted Navigation Control
 *
 * Client-side search bar for category/listing pages.
 * - The parent Server Component reads ?q= and passes it to the API.
 * - Any ?q= param causes generateMetadata to emit noindex + canonical to base URL,
 *   preventing duplicate indexing of filtered pages.
 */
export function FacetedFilterBar({ placeholder = "Search products…" }: Props) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [isPending, startTransition] = useTransition();
  const isIndustrial = siteConfig.layout === "industrial";

  const q = searchParams.get("q") ?? "";

  const handleChange = useCallback(
    (value: string) => {
      const params = new URLSearchParams(searchParams.toString());
      if (value.trim()) {
        params.set("q", value.trim());
      } else {
        params.delete("q");
      }
      // Reset to page 1 when search changes
      params.delete("page");
      startTransition(() => {
        router.replace(`${pathname}?${params.toString()}`, { scroll: false });
      });
    },
    [pathname, router, searchParams]
  );

  return (
    <div className="flex items-center gap-2">
      <div className="relative flex-1 max-w-xs">
        <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 text-sm">🔍</span>
        <input
          type="search"
          defaultValue={q}
          onChange={(e) => handleChange(e.target.value)}
          placeholder={placeholder}
          className={isIndustrial
            ? "w-full border border-gray-300 bg-white py-2 pl-8 pr-4 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30"
            : "w-full pl-8 pr-4 py-2 rounded-lg border border-gray-200 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-300"}
          aria-label="Filter products"
        />
      </div>
      {isPending && (
        <span className={isIndustrial ? "animate-pulse text-[11px] font-black uppercase tracking-[0.16em] text-gray-500" : "text-xs text-gray-400 animate-pulse"}>Filtering…</span>
      )}
      {q && !isPending && (
        <button
          onClick={() => handleChange("")}
          className={isIndustrial
            ? "text-[11px] font-black uppercase tracking-[0.16em] text-gray-500 underline hover:text-gray-800"
            : "text-xs text-gray-400 hover:text-gray-600 underline"}
        >
          Clear
        </button>
      )}
    </div>
  );
}
