import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { PackagingProductPage } from "@/templates/custom-packaging/components/PackagingSite";
import { customPackagingData } from "@/templates/custom-packaging/data";
export function generateStaticParams(){return customPackagingData.products.map(product=>({productSlug:product.slug}))}
export async function generateMetadata({params}:{params:Promise<{productSlug:string}>}):Promise<Metadata>{const{productSlug}=await params;const product=customPackagingData.products.find(item=>item.slug===productSlug);return product?{title:`${product.name} | Tuckform Demo`,description:product.shortDescription}:{}}
export default async function Page({params}:{params:Promise<{productSlug:string}>}){const{productSlug}=await params;const product=customPackagingData.products.find(item=>item.slug===productSlug);if(!product)notFound();return <PackagingProductPage product={product}/>}
