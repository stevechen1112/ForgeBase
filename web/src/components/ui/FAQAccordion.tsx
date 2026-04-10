"use client";

import { useState } from "react";
import type { FAQItem } from "@/types/content";
import { trackFAQExpand } from "@/lib/analytics";
import { ChevronDown } from "lucide-react";
import { siteConfig } from "@/lib/siteConfig";

type Props = { items: FAQItem[] };

export function FAQAccordion({ items }: Props) {
  const [openIndex, setOpenIndex] = useState<number | null>(null);
  const isIndustrial = siteConfig.layout === "industrial";

  function toggle(index: number) {
    const isOpening = openIndex !== index;
    setOpenIndex((prev) => (prev === index ? null : index));
    if (isOpening) trackFAQExpand(items[index].id);
  }

  return (
    <div className={isIndustrial ? "divide-y border border-gray-300 bg-white" : "divide-y rounded-xl border bg-card"}>
      {items.map((item, i) => (
        <div key={item.id}>
          <button
            type="button"
            onClick={() => toggle(i)}
            className={isIndustrial
              ? "flex w-full items-center justify-between px-5 py-4 text-left transition-colors hover:bg-primary/5"
              : "flex w-full items-center justify-between px-6 py-4 text-left hover:bg-muted/30 transition-colors"}
            aria-expanded={openIndex === i}
          >
            <span className={isIndustrial ? "text-sm font-bold uppercase tracking-wide text-gray-900" : "text-sm font-medium"}>{item.question}</span>
            <ChevronDown
              className={`ml-4 h-5 w-5 flex-shrink-0 ${isIndustrial ? "text-primary" : "text-muted-foreground"} transition-transform duration-200 ${
                openIndex === i ? "rotate-180" : ""
              }`}
              aria-hidden="true"
            />
          </button>
          {openIndex === i && (
            <div
              className={isIndustrial
                ? "px-5 pb-5 text-sm leading-relaxed text-gray-600 [&_ol]:list-decimal [&_ol]:pl-4 [&_p]:mb-2 [&_p:last-child]:mb-0 [&_ul]:list-disc [&_ul]:pl-4"
                : "px-6 pb-5 text-sm text-muted-foreground leading-relaxed [&_p]:mb-2 [&_p:last-child]:mb-0 [&_ul]:list-disc [&_ul]:pl-4 [&_ol]:list-decimal [&_ol]:pl-4"}
              // answer is richtext HTML authored in the admin CMS (not user input)
              dangerouslySetInnerHTML={{ __html: item.answer }}
            />
          )}
        </div>
      ))}
    </div>
  );
}
