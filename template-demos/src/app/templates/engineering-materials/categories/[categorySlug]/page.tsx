import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { MaterialCategoryPage } from "@/templates/engineering-materials/components/MaterialsSite";
import { engineeringMaterialsData } from "@/templates/engineering-materials/data";
export function generateStaticParams(){return engineeringMaterialsData.categories.map(category=>({categorySlug:category.slug}))}
export async function generateMetadata({params}:{params:Promise<{categorySlug:string}>}):Promise<Metadata>{const {categorySlug}=await params;const category=engineeringMaterialsData.categories.find(item=>item.slug===categorySlug);return category?{title:`${category.name} | Matera Demo`,description:category.description}:{}}
export default async function Page({params}:{params:Promise<{categorySlug:string}>}){const {categorySlug}=await params;if(!engineeringMaterialsData.categories.some(item=>item.slug===categorySlug))notFound();return <MaterialCategoryPage categorySlug={categorySlug}/>}
