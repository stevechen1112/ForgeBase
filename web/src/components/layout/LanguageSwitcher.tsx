"use client";

import { useLocale } from "next-intl";
import { usePathname } from "@/i18n/navigation";
import { LOCALE_NATIVE_NAMES, PUBLIC_LOCALES, type Locale } from "@/i18n/routing";
import { withBasePath } from "@/lib/basePath";
import { localizedPath } from "@/lib/localizedPath";
import { useMessageNamespace } from "@/lib/messages";
import { cn } from "@/lib/utils";

export function LanguageSwitcher({ className }: { className?: string }) {
  const locale = useLocale() as Locale;
  const pathname = usePathname() || "/";
  const copy = useMessageNamespace<{ langSwitch: string }>("header");

  return (
    <label className={cn("inline-flex items-center", className)}>
      <span className="sr-only">{copy.langSwitch}</span>
      <select
        aria-label={copy.langSwitch}
        value={locale}
        onChange={(event) => {
          const destination = withBasePath(localizedPath(event.target.value, pathname));
          const destinationUrl = new URL(destination, window.location.origin);
          destinationUrl.search = window.location.search;
          destinationUrl.hash = window.location.hash;
          // The locale provider lives in the root layout. A document navigation
          // guarantees the server rebuilds it with the destination message pack.
          window.location.assign(destinationUrl);
        }}
        className="max-w-32 cursor-pointer rounded-md border border-current/20 bg-transparent px-2 py-1.5 text-xs font-semibold text-inherit outline-none focus-visible:ring-2 focus-visible:ring-primary"
      >
        {PUBLIC_LOCALES.map((candidate) => (
          <option key={candidate} value={candidate} className="bg-background text-foreground">
            {LOCALE_NATIVE_NAMES[candidate]}
          </option>
        ))}
      </select>
    </label>
  );
}
