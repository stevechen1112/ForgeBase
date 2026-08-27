import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { industrialMachineryData } from "@/templates/industrial-machinery/data";
import { MachineryProductDetailPage } from "@/templates/industrial-machinery/components/MachinerySite";

export function generateStaticParams() {
  return industrialMachineryData.products.map((product) => ({ productSlug: product.slug }));
}

export const dynamicParams = false;

export async function generateMetadata({ params }: { params: Promise<{ productSlug: string }> }): Promise<Metadata> {
  const { productSlug } = await params;
  const product = industrialMachineryData.products.find((item) => item.slug === productSlug);
  if (!product) return {};
  return { title: `${product.name} | Vantera Demo`, description: `${product.shortDescription} Fictional equipment content for the ForgeBase Industrial Machinery template.` };
}

export default async function Page({ params }: { params: Promise<{ productSlug: string }> }) {
  const { productSlug } = await params;
  const product = industrialMachineryData.products.find((item) => item.slug === productSlug);
  if (!product) notFound();
  return <MachineryProductDetailPage product={product} />;
}
