import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { ElectronicsCategoryPage } from "@/templates/electronic-components/components/ElectronicSite";
import { electronicComponentsData } from "@/templates/electronic-components/data";

export function generateStaticParams() { return electronicComponentsData.categories.map((category) => ({ categorySlug: category.slug })); }
export const dynamicParams = false;

export async function generateMetadata({ params }: { params: Promise<{ categorySlug: string }> }): Promise<Metadata> {
  const { categorySlug } = await params;
  const category = electronicComponentsData.categories.find((item) => item.slug === categorySlug);
  return category ? { title: `${category.name} | Veltrix Demo`, description: category.description } : {};
}

export default async function Page({ params }: { params: Promise<{ categorySlug: string }> }) {
  const { categorySlug } = await params;
  if (!electronicComponentsData.categories.some((item) => item.slug === categorySlug)) notFound();
  return <ElectronicsCategoryPage categorySlug={categorySlug} />;
}
