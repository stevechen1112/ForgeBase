import Link from "next/link";
import type { ReactNode } from "react";
import type { TemplateCTA } from "@/contracts/forgebase";

export function DemoCTA({
  cta,
  className,
  children,
}: {
  cta: TemplateCTA;
  className?: string;
  children?: ReactNode;
}) {
  return (
    <Link
      href={cta.href}
      className={className}
      data-cta-id={cta.id}
      data-cta-intent={cta.intent}
    >
      {children ?? cta.label}
    </Link>
  );
}
