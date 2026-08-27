import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { MaterialProductPage } from "@/templates/engineering-materials/components/MaterialsSite";
import { engineeringMaterialsData } from "@/templates/engineering-materials/data";
export function generateStaticParams(){return engineeringMaterialsData.products.map(product=>({productSlug:product.slug}))}
export async function generateMetadata({params}:{params:Promise<{productSlug:string}>}):Promise<Metadata>{const {productSlug}=await params;const product=engineeringMaterialsData.products.find(item=>item.slug===productSlug);return product?{title:`${product.name} | Matera Demo`,description:product.shortDescription}:{}}
export default async function Page({params}:{params:Promise<{productSlug:string}>}){const {productSlug}=await params;const product=engineeringMaterialsData.products.find(item=>item.slug===productSlug);if(!product)notFound();return <MaterialProductPage product={product}/>}
