/**
 * Theme component registry.
 *
 * Maps layout variants to their component implementations.
 * Header/Footer are switched in the root layout.
 * Homepage is switched in page.tsx.
 */

export type { LayoutVariant } from "@/lib/siteConfig";

// Industrial theme barrel
export { IndustrialHeader } from "./industrial/IndustrialHeader";
export { IndustrialFooter } from "./industrial/IndustrialFooter";
export { IndustrialHero } from "./industrial/IndustrialHero";
export { IndustrialHomePage } from "./industrial/IndustrialHomePage";
