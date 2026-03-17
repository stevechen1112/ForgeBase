import type { Product, ProductCategory } from "@/types/content";

const GENERATED_BASE = "/demo/handtool-company/assets/generated";
const V = "?v=2"; // cache-buster: bump to force browser refresh

export const HOME_HERO_IMAGE = `${GENERATED_BASE}/homepage-hero-northforge-manufacturer.png${V}`;
export const ABOUT_HERO_IMAGE = `${GENERATED_BASE}/about-factory-hero-northforge.png${V}`;
export const PRODUCTS_HERO_IMAGE = `${GENERATED_BASE}/category-toolkits-storage-hero.png${V}`;
export const QUALITY_INSPECTION_IMAGE = `${GENERATED_BASE}/capability-quality-inspection.png${V}`;
export const CUSTOM_PACKAGING_IMAGE = `${GENERATED_BASE}/capability-custom-packaging-oem.png${V}`;

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
  "NFT-TW250":   `${GENERATED_BASE}/product-nft-tw250-main.png`,
  "NFT-TW380":   `${GENERATED_BASE}/product-nft-tw380-main.png`,
  "NFT-TW500":   `${GENERATED_BASE}/product-nft-tw500-main.png`,
  "NFT-TWA120":  `${GENERATED_BASE}/product-nft-twa120-main.png`,
  "NFT-RH372":   `${GENERATED_BASE}/product-nft-rh372-main.png`,
  "NFT-RH390F":  `${GENERATED_BASE}/product-nft-rh390f-main.png`,
  "NFT-SS094":   `${GENERATED_BASE}/product-nft-ss094-main.png`,
  "NFT-SS137":   `${GENERATED_BASE}/product-nft-ss137-main.png`,
  // Insulated Electrical Tools
  "NFT-ID006":   `${GENERATED_BASE}/product-nft-id006-main.png`,
  "NFT-ID013":   `${GENERATED_BASE}/product-nft-id013-main.png`,
  "NFT-IP200":   `${GENERATED_BASE}/product-nft-ip200-main.png`,
  "NFT-IP160N":  `${GENERATED_BASE}/product-nft-ip160n-main.png`,
  "NFT-IP165D":  `${GENERATED_BASE}/product-nft-ip165d-main.png`,
  "NFT-EK018":   `${GENERATED_BASE}/product-nft-ek018-main.png`,
  // Striking & Workshop Tools
  "NFT-DH045":   `${GENERATED_BASE}/product-nft-dh045-main.png`,
  "NFT-DH060":   `${GENERATED_BASE}/product-nft-dh060-main.png`,
  "NFT-SM40":    `${GENERATED_BASE}/product-nft-sm40-main.png`,
  "NFT-EH24":    `${GENERATED_BASE}/product-nft-eh24-main.png`,
  "NFT-PB4S":    `${GENERATED_BASE}/product-nft-pb4s-main.png`,
  "NFT-CS6P":    `${GENERATED_BASE}/product-nft-cs6p-main.png`,
  // Automotive Service Tools
  "NFT-AM12F":   `${GENERATED_BASE}/product-nft-am12f-main.png`,
  "NFT-AMBC7":   `${GENERATED_BASE}/product-nft-ambc7-main.png`,
  "NFT-AMSP5":   `${GENERATED_BASE}/product-nft-amsp5-main.png`,
  "NFT-AMPU3":   `${GENERATED_BASE}/product-nft-ampu3-main.png`,
  "NFT-AMHTM":   `${GENERATED_BASE}/product-nft-amhtm-main.png`,
  "NFT-AMTR8":   `${GENERATED_BASE}/product-nft-amtr8-main.png`,
  // Custom Toolkits & Storage
  "NFT-KTMEV1":  `${GENERATED_BASE}/product-nft-ktmev1-main.png`,
  "NFT-KTBC89":  `${GENERATED_BASE}/product-nft-ktbc89-main.png`,
  "NFT-KTEC24":  `${GENERATED_BASE}/product-nft-ktec24-main.png`,
  "NFT-KTWS128": `${GENERATED_BASE}/product-nft-ktws128-main.png`,
  "NFT-KTPLR56": `${GENERATED_BASE}/product-nft-ktplr56-main.png`,
  "NFT-KTFM42":  `${GENERATED_BASE}/product-nft-ktfm42-main.png`,
};

export function getCategoryHeroImage(slug: string, fallback?: string | null): string | null {
  const img = CATEGORY_HERO_BY_SLUG[slug] ?? fallback ?? null;
  return img ? `${img}${V}` : null;
}

export function getCategoryCardImage(category: Pick<ProductCategory, "slug" | "image_url">): string | null {
  return getCategoryHeroImage(category.slug, category.image_url);
}

export function getApplicationImage(slug: string, fallback?: string | null): string | null {
  const img = APPLICATION_IMAGE_BY_SLUG[slug] ?? fallback ?? null;
  return img ? `${img}${V}` : null;
}

export function getProductImage(product: Pick<Product, "model_number">, categorySlug?: string): string | null {
  const img = PRODUCT_IMAGE_BY_MODEL[product.model_number] ?? null;
  if (img) return `${img}${V}`;
  return categorySlug ? getCategoryHeroImage(categorySlug) : null;
}