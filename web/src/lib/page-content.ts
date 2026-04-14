import type { Page } from "@/types/content";

type LinkAction = {
  label: string;
  href: string;
};

type BlockItem = {
  title?: string;
  description?: string;
  value?: string;
  label?: string;
  lines?: string[];
};

export type HeroBlock = {
  type: "hero";
  eyebrow?: string;
  title?: string;
  description?: string;
  backgroundImageUrl?: string;
  primaryCta?: LinkAction;
  secondaryCta?: LinkAction;
  align?: "left" | "center";
};

export type RichTextBlock = {
  type: "rich-text";
  eyebrow?: string;
  title?: string;
  content: string;
};

export type FeatureGridBlock = {
  type: "feature-grid";
  eyebrow?: string;
  title?: string;
  description?: string;
  columns?: 2 | 3 | 4;
  items: BlockItem[];
};

export type StatsBlock = {
  type: "stats";
  eyebrow?: string;
  title?: string;
  items: Array<{ value: string; label: string }>;
};

export type ChecklistBlock = {
  type: "checklist";
  eyebrow?: string;
  title?: string;
  description?: string;
  items: string[];
};

export type CTASectionBlock = {
  type: "cta";
  eyebrow?: string;
  title: string;
  description?: string;
  primaryCta: LinkAction;
  secondaryCta?: LinkAction;
};

export type ContactFormBlock = {
  type: "contact-form";
  eyebrow?: string;
  title?: string;
  description?: string;
};

export type ContactCardsBlock = {
  type: "contact-cards";
  eyebrow?: string;
  title?: string;
  items: BlockItem[];
};

export type SplitBlock = {
  type: "split";
  eyebrow?: string;
  title?: string;
  content?: string;
  imageUrl?: string;
  imageAlt?: string;
  primaryCta?: LinkAction;
};

export type FlexiblePageBlock =
  | HeroBlock
  | RichTextBlock
  | FeatureGridBlock
  | StatsBlock
  | ChecklistBlock
  | CTASectionBlock
  | ContactFormBlock
  | ContactCardsBlock
  | SplitBlock;

export function parsePageBlocks(page: Pick<Page, "body">): FlexiblePageBlock[] | null {
  if (!page.body) {
    return null;
  }

  try {
    const parsed = JSON.parse(page.body) as unknown;
    if (Array.isArray(parsed)) {
      return parsed as FlexiblePageBlock[];
    }
    if (parsed && typeof parsed === "object" && Array.isArray((parsed as { blocks?: unknown[] }).blocks)) {
      return (parsed as { blocks: FlexiblePageBlock[] }).blocks;
    }
  } catch {
    return null;
  }

  return null;
}

export function parseStructuredData(page: Pick<Page, "structured_data">): Record<string, unknown> | null {
  if (!page.structured_data) {
    return null;
  }

  try {
    const parsed = JSON.parse(page.structured_data) as Record<string, unknown>;
    return parsed && typeof parsed === "object" ? parsed : null;
  } catch {
    return null;
  }
}

export function pageBodyLooksLikeHtml(body: string | null | undefined): boolean {
  return Boolean(body && /<\/?[a-z][\s\S]*>/i.test(body));
}