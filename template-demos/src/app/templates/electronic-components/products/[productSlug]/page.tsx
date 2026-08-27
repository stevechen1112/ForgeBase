import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { ElectronicsProductPage } from "@/templates/electronic-components/components/ElectronicSite";
import { electronicComponentsData } from "@/templates/electronic-components/data";

export function generateStaticParams() { return electronicComponentsData.products.map((product) => ({ productSlug: product.slug })); }
export const dynamicParams = false;

export async function generateMetadata({ params }: { params: Promise<{ productSlug: string }> }): Promise<Metadata> {
  const { productSlug } = await params;
  const product = electronicComponentsData.products.find((item) => item.slug === productSlug);
  return product ? { title: `${product.modelNumber} | Veltrix Demo`, description: `${product.shortDescription} Fictional component data for the ForgeBase Electronic Components template.` } : {};
}

export default async function Page({ params }: { params: Promise<{ productSlug: string }> }) {
  const { productSlug } = await params;
  const product = electronicComponentsData.products.find((item) => item.slug === productSlug);
  if (!product) notFound();
  return <ElectronicsProductPage product={product} />;
}
