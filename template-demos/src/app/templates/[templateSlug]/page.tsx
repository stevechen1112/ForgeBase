import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getRegisteredTemplate, registeredTemplates } from "@/templates/registry";

export function generateStaticParams() {
  return registeredTemplates
    .filter((template) => template.manifest.status === "ready")
    .map((template) => ({ templateSlug: template.manifest.slug }));
}

export const dynamicParams = false;

export async function generateMetadata({ params }: { params: Promise<{ templateSlug: string }> }): Promise<Metadata> {
  const { templateSlug } = await params;

  return getRegisteredTemplate(templateSlug)?.metadata ?? {};
}

export default async function TemplatePage({ params }: { params: Promise<{ templateSlug: string }> }) {
  const { templateSlug } = await params;

  const template = getRegisteredTemplate(templateSlug);
  if (!template || template.manifest.status !== "ready") notFound();

  const TemplateComponent = template.component;
  return <TemplateComponent />;
}
