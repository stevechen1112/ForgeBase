import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { precisionMachiningData } from "@/templates/precision-machining/data";
import { ProductDetailPage } from "@/templates/precision-machining/components/PrecisionSitePages";

export function generateStaticParams() {
  return precisionMachiningData.products.map((product) => ({ productSlug: product.slug }));
}

export const dynamicParams = false;

export async function generateMetadata({ params }: { params: Promise<{ productSlug: string }> }): Promise<Metadata> {
  const { productSlug } = await params;
  const product = precisionMachiningData.products.find((item) => item.slug === productSlug);

  if (!product) return {};

  return {
    title: `${product.name} | AxisForm Demo`,
    description: `${product.shortDescription} Fictional product content for the ForgeBase precision-machining template.`,
  };
}

export default async function Page({ params }: { params: Promise<{ productSlug: string }> }) {
  const { productSlug } = await params;
  const product = precisionMachiningData.products.find((item) => item.slug === productSlug);
  if (!product) notFound();
  return <ProductDetailPage product={product} />;
}
