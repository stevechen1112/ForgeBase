import type { Product, ProductCategory, Application } from "@/types/content";
import { siteConfig, type SiteAssetManifest, type SiteConfig } from "@/lib/siteConfig";

type AssetConfigLike = Pick<SiteConfig, "assetManifest">;

const V = "?v=4";

function withVersion(path?: string | null): string | null {
  if (!path) {
    return null;
  }
  return path.includes("?") ? path : `${path}${V}`;
}

function getManifest(config: AssetConfigLike = siteConfig): SiteAssetManifest | undefined {
  return config.assetManifest;
}

/**
 * Seed CMS still points at legacy `/assets/*.jpg` paths that were never shipped.
 * Those miss on disk and `demoAssetRoute` returns lookalike SVG placeholders.
 * Prefer generated manifest assets whenever the CMS URL is empty or still a legacy placeholder.
 */
function isLegacyDemoPlaceholder(path?: string | null): boolean {
  if (!path) {
    return true;
  }
  return /\/demo\/[^/]+\/assets\/(?!generated\/)/.test(path);
}

function pickAsset(cmsPath?: string | null, manifestPath?: string | null): string | null {
  if (!isLegacyDemoPlaceholder(cmsPath)) {
    return cmsPath ?? null;
  }
  return manifestPath ?? cmsPath ?? null;
}

export function getHomeHeroImage(config: AssetConfigLike = siteConfig): string | null {
  return withVersion(getManifest(config)?.homeHero);
}

export function getAboutHeroImage(config: AssetConfigLike = siteConfig): string | null {
  return withVersion(getManifest(config)?.aboutHero);
}

export function getProductsHeroImage(config: AssetConfigLike = siteConfig): string | null {
  return withVersion(getManifest(config)?.productsHero);
}

export function getQualityInspectionImage(config: AssetConfigLike = siteConfig): string | null {
  return withVersion(getManifest(config)?.qualityInspection);
}

export function getCustomPackagingImage(config: AssetConfigLike = siteConfig): string | null {
  return withVersion(getManifest(config)?.customPackaging);
}

export function getCategoryHeroImage(
  slug: string,
  fallback?: string | null,
  config: AssetConfigLike = siteConfig
): string | null {
  const manifest = getManifest(config);
  return withVersion(pickAsset(fallback, manifest?.categoryBySlug?.[slug]));
}

export function getCategoryCardImage(
  category: Pick<ProductCategory, "slug" | "image_url">,
  config: AssetConfigLike = siteConfig
): string | null {
  return getCategoryHeroImage(category.slug, category.image_url, config);
}

export function getApplicationImage(
  application: Pick<Application, "slug" | "hero_image_url">,
  config: AssetConfigLike = siteConfig
): string | null {
  const manifest = getManifest(config);
  return withVersion(
    pickAsset(application.hero_image_url, manifest?.applicationBySlug?.[application.slug]),
  );
}

export function getProductImage(
  product: Pick<Product, "model_number"> & Partial<Pick<Product, "image_url" | "og_image_url">>,
  categorySlug?: string,
  config: AssetConfigLike = siteConfig
): string | null {
  const manifest = getManifest(config);
  const manifestImage = manifest?.productByKey?.[product.model_number] ?? null;
  const cmsImage = product.image_url || product.og_image_url;
  const image = pickAsset(cmsImage, manifestImage);
  if (image) {
    return withVersion(image);
  }
  return categorySlug ? getCategoryHeroImage(categorySlug, undefined, config) : null;
}

export const HOME_HERO_IMAGE = getHomeHeroImage();
export const ABOUT_HERO_IMAGE = getAboutHeroImage();
export const PRODUCTS_HERO_IMAGE = getProductsHeroImage();
export const QUALITY_INSPECTION_IMAGE = getQualityInspectionImage();
export const CUSTOM_PACKAGING_IMAGE = getCustomPackagingImage();
