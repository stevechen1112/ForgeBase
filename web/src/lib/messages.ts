import { useMessages } from "next-intl";
import { getMessages } from "next-intl/server";

type MessageTree = Record<string, unknown>;

function getNestedValue(messages: MessageTree, path: string): unknown {
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

export async function getMessageNamespace<T>(path: string): Promise<T> {
  const messages = (await getMessages()) as MessageTree;
  return getNestedValue(messages, path) as T;
}