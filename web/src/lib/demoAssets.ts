import type { Product, ProductCategory } from "@/types/content";

const GENERATED_BASE = "/demo/handtool-company/assets/generated";

export const HOME_HERO_IMAGE = `${GENERATED_BASE}/homepage-hero-northforge-manufacturer.png`;
export const ABOUT_HERO_IMAGE = `${GENERATED_BASE}/about-factory-hero-northforge.png`;
export const PRODUCTS_HERO_IMAGE = `${GENERATED_BASE}/category-toolkits-storage-hero.png`;
export const QUALITY_INSPECTION_IMAGE = `${GENERATED_BASE}/capability-quality-inspection.png`;
export const CUSTOM_PACKAGING_IMAGE = `${GENERATED_BASE}/capability-custom-packaging-oem.png`;

const CATEGORY_HERO_BY_SLUG: Record<string, string> = {
  "torque-and-socket-tools": `${GENERATED_BASE}/category-torque-socket-tools-hero.png`,
  "insulated-electrical-tools": `${GENERATED_BASE}/category-insulated-electrical-tools-hero.png`,
  "striking-and-workshop-tools": `${GENERATED_BASE}/category-striking-workshop-tools-hero.png`,
  "automotive-service-tools": `${GENERATED_BASE}/category-automotive-service-tools-hero.png`,
  "custom-toolkits-and-storage": `${GENERATED_BASE}/category-toolkits-storage-hero.png`,
};

const APPLICATION_IMAGE_BY_SLUG: Record<string, string> = {
  "automotive-aftermarket-service": `${GENERATED_BASE}/application-automotive-aftermarket-service.png`,
  "industrial-maintenance-and-mro": `${GENERATED_BASE}/application-industrial-maintenance-mro.png`,
  "electrical-installation-and-utility-work": `${GENERATED_BASE}/application-electrical-installation-utility.png`,
  "workshop-assembly-and-repair": `${GENERATED_BASE}/application-workshop-assembly-repair.png`,
  "private-label-tool-programs": `${GENERATED_BASE}/application-private-label-programs.png`,
  "field-service-and-mobile-maintenance": `${GENERATED_BASE}/application-field-service-mobile.png`,
};

const PRODUCT_IMAGE_BY_MODEL: Record<string, string> = {
  // Torque & Socket Tools
  "NFT-TW380": `${GENERATED_BASE}/product-nft-tw380-main.png`,
  "NFT-TW500": `${GENERATED_BASE}/product-nft-tw500-main.png`,
  // Insulated Electrical Tools
  "NFT-ID006": `${GENERATED_BASE}/product-nft-id006-main.png`,
  "NFT-EK018": `${GENERATED_BASE}/product-nft-ek018-main.png`,
  "NFT-IP200": `${GENERATED_BASE}/product-nft-ip200-main.png`,
  // Striking & Workshop Tools
  "NFT-DH045": `${GENERATED_BASE}/product-nft-dh045-main.png`,
  // Automotive Service Tools
  "NFT-AMBC7": `${GENERATED_BASE}/product-nft-ambc7-main.png`,
  "NFT-AMSP5": `${GENERATED_BASE}/product-nft-amsp5-main.png`,
  // Custom Toolkits & Storage
  "NFT-KTBC89": `${GENERATED_BASE}/product-nft-ktbc89-main.png`,
  "NFT-KTMEV1": `${GENERATED_BASE}/product-nft-ktmev1-main.png`,
  "NFT-KTFM42": `${GENERATED_BASE}/product-nft-ktfm42-main.png`,
};

export function getCategoryHeroImage(slug: string, fallback?: string | null): string | null {
  return CATEGORY_HERO_BY_SLUG[slug] ?? fallback ?? null;
}

export function getCategoryCardImage(category: Pick<ProductCategory, "slug" | "image_url">): string | null {
  return getCategoryHeroImage(category.slug, category.image_url);
}

export function getApplicationImage(slug: string, fallback?: string | null): string | null {
  return APPLICATION_IMAGE_BY_SLUG[slug] ?? fallback ?? null;
}

export function getProductImage(product: Pick<Product, "model_number">, categorySlug?: string): string | null {
  return PRODUCT_IMAGE_BY_MODEL[product.model_number] ?? (categorySlug ? getCategoryHeroImage(categorySlug) : null);
}