import { cn } from "@/lib/utils";

type Props = {
  name: string;
  mark: string;
  logoUrl?: string | null;
  className?: string;
  imageClassName?: string;
};

export function BrandMark({ name, mark, logoUrl, className, imageClassName }: Props) {
  if (logoUrl) {
    return (
      // eslint-disable-next-line @next/next/no-img-element
      <img src={logoUrl} alt={name} className={cn("h-8 w-auto max-w-32 object-contain", imageClassName)} />
    );
  }
  return (
    <div className={cn("flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-[11px] font-bold text-primary-foreground", className)}>
      {mark}
    </div>
  );
}
