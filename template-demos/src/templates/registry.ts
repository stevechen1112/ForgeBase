import type { Metadata } from "next";
import type { ComponentType } from "react";
import type { TemplateManifest } from "@/contracts/forgebase";
import { precisionMachiningManifest } from "./precision-machining/manifest";
import { PrecisionMachiningTemplate } from "./precision-machining/components/PrecisionMachiningTemplate";
import { industrialMachineryManifest } from "./industrial-machinery/manifest";
import { IndustrialMachineryTemplate } from "./industrial-machinery/components/MachinerySite";
import { electronicComponentsManifest } from "./electronic-components/manifest";
import { ElectronicComponentsTemplate } from "./electronic-components/components/ElectronicSite";
import { industrialAutomationManifest } from "./industrial-automation/manifest";
import { IndustrialAutomationTemplate } from "./industrial-automation/components/AutomationSite";
import { engineeringMaterialsManifest } from "./engineering-materials/manifest";
import { EngineeringMaterialsTemplate } from "./engineering-materials/components/MaterialsSite";
import { customPackagingManifest } from "./custom-packaging/manifest";
import { CustomPackagingTemplate } from "./custom-packaging/components/PackagingSite";

export interface RegisteredTemplate {
  manifest: TemplateManifest;
  component: ComponentType;
  metadata: Metadata;
}

export const registeredTemplates: RegisteredTemplate[] = [
  {
    manifest: precisionMachiningManifest,
    component: PrecisionMachiningTemplate,
    metadata: {
      title: "Precision CNC Machining | AxisForm Demo",
      description: "A fictional, full-site B2B precision-machining template demonstrating parts, capabilities, quality and drawing-led RFQ content.",
    },
  },
  {
    manifest: industrialMachineryManifest,
    component: IndustrialMachineryTemplate,
    metadata: {
      title: "Industrial Production Systems | Vantera Demo",
      description: "A fictional full-site industrial machinery template for equipment comparison, application engineering, service planning and system RFQ.",
    },
  },
  {
    manifest: electronicComponentsManifest,
    component: ElectronicComponentsTemplate,
    metadata: {
      title: "Electronic Components | Veltrix Demo",
      description: "A fictional full-site electronic-components template for part search, parametric comparison, technical evidence and sample requests.",
    },
  },
  {
    manifest: industrialAutomationManifest,
    component: IndustrialAutomationTemplate,
    metadata: {
      title: "Industrial Automation & Robotics | Kinetra Demo",
      description: "A fictional full-site industrial-automation template for system architecture, application diagnosis, integration capability and consultation conversion.",
      openGraph: { images: ["/templates/industrial-automation/social-preview.png"] },
    },
  },
  {
    manifest: engineeringMaterialsManifest,
    component: EngineeringMaterialsTemplate,
    metadata: {
      title: "Engineering Materials | Matera Demo",
      description: "A fictional full-site engineering-material template for condition-led grade selection, evidence review and sample requests.",
      openGraph: { images: ["/templates/engineering-materials/social-preview.png"] },
    },
  },
  {
    manifest: customPackagingManifest,
    component: CustomPackagingTemplate,
    metadata: {
      title: "Custom Packaging Manufacturing | Tuckform Demo",
      description: "A fictional full-site custom packaging template for structural systems, sampling, print and configuration-led quotation.",
      openGraph: { images: ["/templates/custom-packaging/social-preview.png"] },
    },
  },
];

export const templateRegistry: TemplateManifest[] = [
  ...registeredTemplates.map((template) => template.manifest),
];

export function getTemplateManifest(slug: string) {
  return templateRegistry.find((template) => template.slug === slug);
}

export function getReadyTemplates() {
  return templateRegistry.filter((template) => template.status === "ready");
}

export function getRegisteredTemplate(slug: string) {
  return registeredTemplates.find((template) => template.manifest.slug === slug);
}
