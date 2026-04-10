import { Link } from "@/i18n/navigation";
import { cn } from "@/lib/utils";

type BreadcrumbItem = {
  label: string;
  href?: string;
};

type IndustrialPageHeroProps = {
  items: BreadcrumbItem[];
  title: string;
  description?: string;
  eyebrow?: string;
  imageSrc?: string;
  children?: React.ReactNode;
  className?: string;
  contentClassName?: string;
};

export function IndustrialPageHero({
  items,
  title,
  description,
  eyebrow,
  imageSrc,
  children,
  className,
  contentClassName,
}: IndustrialPageHeroProps) {
  return (
    <section className={cn("relative overflow-hidden border-b border-gray-800 bg-gray-950 text-white", className)}>
      {imageSrc && (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={imageSrc}
          alt=""
          className="absolute inset-0 h-full w-full object-cover opacity-30"
          aria-hidden="true"
        />
      )}
      <div
        className="pointer-events-none absolute inset-0 opacity-[0.06]"
        style={{
          backgroundImage:
            "repeating-linear-gradient(135deg, transparent, transparent 28px, white 28px, white 30px)",
        }}
      />
      <div className="absolute inset-0 bg-gradient-to-r from-gray-950 via-gray-950/92 to-gray-900/70" />
      <div className={cn("relative mx-auto max-w-7xl px-6 py-14 sm:py-16", contentClassName)}>
        <nav aria-label="Breadcrumb" className="mb-4 text-[11px] font-bold uppercase tracking-[0.16em] text-gray-500">
          <ol className="flex flex-wrap items-center gap-2">
            {items.map((item, index) => (
              <li key={`${item.label}-${index}`} className="flex items-center gap-2">
                {index > 0 && <span className="text-primary">/</span>}
                {item.href && index < items.length - 1 ? (
                  <Link href={item.href} className="transition-colors hover:text-white">
                    {item.label}
                  </Link>
                ) : (
                  <span className={index === items.length - 1 ? "text-white" : undefined}>{item.label}</span>
                )}
              </li>
            ))}
          </ol>
        </nav>
        {eyebrow && (
          <div className="mb-4 flex items-center gap-3">
            <div className="h-6 w-1.5 bg-primary" />
            <span className="text-[10px] font-black uppercase tracking-[0.2em] text-primary">{eyebrow}</span>
          </div>
        )}
        <h1 className="max-w-4xl text-4xl font-black uppercase tracking-tight sm:text-5xl">{title}</h1>
        {description && (
          <p className="mt-4 max-w-2xl text-base leading-relaxed text-gray-300">{description}</p>
        )}
        {children ? <div className="mt-6">{children}</div> : null}
      </div>
    </section>
  );
}

type IndustrialSectionHeadingProps = {
  eyebrow?: string;
  title: string;
  description?: string;
  align?: "left" | "center";
  className?: string;
};

export function IndustrialSectionHeading({
  eyebrow,
  title,
  description,
  align = "left",
  className,
}: IndustrialSectionHeadingProps) {
  return (
    <div className={cn(align === "center" ? "text-center" : "", className)}>
      {eyebrow && (
        <div className={cn("mb-3 flex items-center gap-3", align === "center" ? "justify-center" : "") }>
          <div className="h-6 w-1.5 bg-primary" />
          <span className="text-[10px] font-black uppercase tracking-[0.2em] text-primary">{eyebrow}</span>
        </div>
      )}
      <h2 className="text-2xl font-black uppercase tracking-tight text-gray-900 sm:text-3xl">{title}</h2>
      {description && (
        <p className={cn("mt-3 text-sm leading-relaxed text-gray-500", align === "center" ? "mx-auto max-w-2xl" : "max-w-xl")}>{description}</p>
      )}
    </div>
  );
}

type IndustrialCtaPanelProps = {
  title: string;
  description: string;
  primaryHref: string;
  primaryLabel: string;
  secondaryHref?: string;
  secondaryLabel?: string;
  className?: string;
};

export function IndustrialCtaPanel({
  title,
  description,
  primaryHref,
  primaryLabel,
  secondaryHref,
  secondaryLabel,
  className,
}: IndustrialCtaPanelProps) {
  return (
    <div className={cn("relative overflow-hidden border border-gray-800 bg-gray-950 px-6 py-8 text-white", className)}>
      <div
        className="pointer-events-none absolute inset-0 opacity-[0.04]"
        style={{
          backgroundImage:
            "repeating-linear-gradient(135deg, transparent, transparent 30px, white 30px, white 32px)",
        }}
      />
      <div className="relative flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h3 className="text-xl font-black uppercase tracking-tight">{title}</h3>
          <p className="mt-2 max-w-2xl text-sm leading-relaxed text-gray-400">{description}</p>
        </div>
        <div className="flex flex-wrap gap-3">
          <Link
            href={primaryHref}
            className="bg-primary px-6 py-3 text-sm font-black uppercase tracking-[0.16em] text-primary-foreground skew-x-[-3deg] hover:brightness-110"
          >
            <span className="block skew-x-[3deg]">{primaryLabel}</span>
          </Link>
          {secondaryHref && secondaryLabel && (
            <Link
              href={secondaryHref}
              className="border border-gray-600 px-6 py-3 text-sm font-bold uppercase tracking-[0.16em] text-white skew-x-[-3deg] hover:border-gray-400"
            >
              <span className="block skew-x-[3deg]">{secondaryLabel}</span>
            </Link>
          )}
        </div>
      </div>
    </div>
  );
}

export const INDUSTRIAL_PROSE_CLASS = "[&_a]:text-primary [&_a]:underline [&_ol]:list-decimal [&_ol]:pl-5 [&_p]:mb-3 [&_p:last-child]:mb-0 [&_ul]:list-disc [&_ul]:pl-5 text-sm leading-relaxed text-gray-600";