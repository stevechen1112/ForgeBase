import "server-only";

import { getLocale, getMessages } from "next-intl/server";
import { getRuntimeSiteConfig } from "@/lib/runtimeSiteConfig";
import { getNestedValue, mergeMessageTrees, resolveSiteCopyOverlay } from "@/lib/messages";

type MessageTree = Record<string, unknown>;

export async function getMessageNamespace<T>(path: string): Promise<T> {
  const [baseMessages, runtimeSiteConfig, locale] = await Promise.all([
    getMessages() as Promise<MessageTree>,
    getRuntimeSiteConfig(),
    getLocale(),
  ]);
  return getNestedValue(
    mergeMessageTrees(baseMessages, resolveSiteCopyOverlay(runtimeSiteConfig.siteCopy, locale)),
    path,
  ) as T;
}
