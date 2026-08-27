import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { AutomationSolutionPage } from "@/templates/industrial-automation/components/AutomationSite";
import { industrialAutomationData } from "@/templates/industrial-automation/data";

export function generateStaticParams() { return industrialAutomationData.products.map((solution) => ({ solutionSlug: solution.slug })); }

export async function generateMetadata({ params }: { params: Promise<{ solutionSlug: string }> }): Promise<Metadata> {
  const { solutionSlug } = await params;
  const solution = industrialAutomationData.products.find((item) => item.slug === solutionSlug);
  return solution ? { title: `${solution.name} | Kinetra Demo`, description: solution.shortDescription } : {};
}

export default async function Page({ params }: { params: Promise<{ solutionSlug: string }> }) {
  const { solutionSlug } = await params;
  const solution = industrialAutomationData.products.find((item) => item.slug === solutionSlug);
  if (!solution) notFound();
  return <AutomationSolutionPage solution={solution} />;
}
