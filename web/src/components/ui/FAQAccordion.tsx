"use client";

import { useState } from "react";
import type { FAQItem } from "@/types/content";
import { trackFAQExpand } from "@/lib/analytics";
import { ChevronDown } from "lucide-react";

type Props = { items: FAQItem[] };

export function FAQAccordion({ items }: Props) {
  const [openIndex, setOpenIndex] = useState<number | null>(null);

  function toggle(index: number) {
    const isOpening = openIndex !== index;
    setOpenIndex((prev) => (prev === index ? null : index));
    if (isOpening) trackFAQExpand(items[index].id);
  }

  return (
    <div className="divide-y rounded-xl border bg-card">
      {items.map((item, i) => (
        <div key={item.id}>
          <button
            type="button"
            onClick={() => toggle(i)}
            className="flex w-full items-center justify-between px-6 py-4 text-left hover:bg-muted/30 transition-colors"
            aria-expanded={openIndex === i}
          >
            <span className="text-sm font-medium">{item.question}</span>
            <ChevronDown
              className={`ml-4 h-5 w-5 flex-shrink-0 text-muted-foreground transition-transform duration-200 ${
                openIndex === i ? "rotate-180" : ""
              }`}
              aria-hidden="true"
            />
          </button>
          {openIndex === i && (
            <div className="px-6 pb-5 text-sm text-muted-foreground leading-relaxed whitespace-pre-line">
              {item.answer}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
