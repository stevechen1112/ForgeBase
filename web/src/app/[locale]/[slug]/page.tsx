import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { FlexiblePageRenderer } from "@/components/pages/FlexiblePageRenderer";
import { getPublishedPageBySlug } from "@/lib/api";
import { resolveLocale } from "@/lib/siteCopy";

type Props = {
  params: Promise<{ locale: string; slug: string }>;
};

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale, slug } = await params;
  const page = await getPublishedPageBySlug(slug, resolveLocale(locale));

  if (!page) {
    return {};
  }

  return {
    title: page.seo_title ?? page.title,
    description: page.seo_description ?? page.subtitle ?? undefined,
    alternates: page.canonical_url ? { canonical: page.canonical_url } : undefined,
    robots: page.noindex ? { index: false, follow: false } : undefined,
    openGraph: page.og_image_url ? { images: [page.og_image_url] } : undefined,
  };
}

export default async function LocalizedCustomPage({ params }: Props) {
  const { locale, slug } = await params;
  const page = await getPublishedPageBySlug(slug, resolveLocale(locale));

  if (!page) {
    notFound();
  }

  return <FlexiblePageRenderer page={page} />;
}