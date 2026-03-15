import type { Product, ProductCategory } from "@/types/content";

const GENERATED_BASE = "/demo/handtool-company/assets/generated";

export const HOME_HERO_IMAGE = `${GENERATED_BASE}/homepage-hero-northforge-manufacturer.png`;
export const ABOUT_HERO_IMAGE = `${GENERATED_BASE}/about-factory-hero-northforge.png`;
export const PRODUCTS_HERO_IMAGE = `${GENERATED_BASE}/category-toolkits-storage-hero.png`;

const CATEGORY_HERO_BY_SLUG: Record<string, string> = {
  "torque-and-socket-tools": `${GENERATED_BASE}/category-torque-socket-tools-hero.png`,
  "insulated-electrical-tools": `${GENERATED_BASE}/category-insulated-electrical-tools-hero.png`,
  "striking-and-workshop-tools": `${GENERATED_BASE}/category-striking-workshop-tools-hero.png`,
  "automotive-service-tools": `${GENERATED_BASE}/category-automotive-service-tools-hero.png`,
  "custom-toolkits-and-storage": `${GENERATED_BASE}/category-toolkits-storage-hero.png`,
};

const PRODUCT_IMAGE_BY_MODEL: Record<string, string> = {
  "NFT-TW380": `${GENERATED_BASE}/product-nft-tw380-main.png`,
  "NFT-ID006": `${GENERATED_BASE}/product-nft-id006-main.png`,
  "NFT-KTBC89": `${GENERATED_BASE}/product-nft-ktbc89-main.png`,
};

export function getCategoryHeroImage(slug: string, fallback?: string | null): string | null {
  return CATEGORY_HERO_BY_SLUG[slug] ?? fallback ?? null;
}

export function getCategoryCardImage(category: Pick<ProductCategory, "slug" | "image_url">): string | null {
  return getCategoryHeroImage(category.slug, category.image_url);
}

export function getProductImage(product: Pick<Product, "model_number">, categorySlug?: string): string | null {
  return PRODUCT_IMAGE_BY_MODEL[product.model_number] ?? (categorySlug ? getCategoryHeroImage(categorySlug) : null);
}