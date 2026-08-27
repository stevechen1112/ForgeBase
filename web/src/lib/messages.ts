import { useMessages } from "next-intl";
import { toContentLocale, toRouteLocale } from "@/lib/contentLocale";

type MessageTree = Record<string, unknown>;

export function resolveSiteCopyOverlay(
  siteCopy: MessageTree | undefined,
  locale: string,
): MessageTree | undefined {
  if (!siteCopy) return undefined;
  const typedSiteCopy = siteCopy as MessageTree & {
    locales?: Record<string, MessageTree>;
    hiddenBlocks?: unknown;
  };
  const { locales } = typedSiteCopy;
  const legacy = Object.fromEntries(
    Object.entries(typedSiteCopy).filter(([key]) => key !== "locales" && key !== "hiddenBlocks"),
  );
  const normalized = toRouteLocale(locale);
  const localeOverlay = locales?.[normalized]
    ?? locales?.[toContentLocale(normalized)]
    ?? locales?.[locale];
  const merged = mergeMessageTrees(legacy, localeOverlay);
  return Object.keys(merged).length ? merged : undefined;
}

export function mergeMessageTrees(base: MessageTree, override?: MessageTree): MessageTree {
  if (!override) return base;
  const merged: MessageTree = { ...base };
  for (const [key, value] of Object.entries(override)) {
    if (
      value && typeof value === "object" && !Array.isArray(value) &&
      merged[key] && typeof merged[key] === "object" && !Array.isArray(merged[key])
    ) {
      merged[key] = mergeMessageTrees(merged[key] as MessageTree, value as MessageTree);
    } else {
      merged[key] = value;
    }
  }
  return merged;
}

export function getNestedValue(messages: MessageTree, path: string): unknown {
  return path.split(".").reduce<unknown>((current, segment) => {
    if (!current || typeof current !== "object" || !(segment in current)) {
      throw new Error(`Missing translation namespace: ${path}`);
    }

    return (current as MessageTree)[segment];
  }, messages);
}

export function useMessageNamespace<T>(path: string): T {
  const messages = useMessages() as MessageTree;
  return getNestedValue(messages, path) as T;
}
