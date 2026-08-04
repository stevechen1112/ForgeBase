import { Link } from "@/i18n/navigation";
import type { Product } from "@/types/content";
import { getProductImage } from "@/lib/demoAssets";
import { siteConfig as defaultSiteConfig, type SiteConfig } from "@/lib/siteConfig";

type Props = {
  product: Product;
  /** Pass undefined when the category slug is not known (e.g. related products on application pages). */
  categorySlug: string | undefined;
  siteConfig?: SiteConfig;
};

export function ProductCard({ product, categorySlug, siteConfig = defaultSiteConfig }: Props) {
  const href = categorySlug
    ? `/products/${categorySlug}/${product.slug}`
    : `/products/${product.slug}`;
  const productImage = getProductImage(product, categorySlug, siteConfig);
  const isIndustrial = siteConfig.layout === "industrial";

  return (
    <Link
      href={href}
      className={isIndustrial
        ? "group flex flex-col border border-gray-300 bg-white p-5 transition-colors hover:border-primary/50 hover:bg-primary/5"
        : "group flex flex-col rounded-xl border border-gray-200 bg-white p-5 shadow-sm transition-shadow hover:shadow-md"}
    >
      {/* Placeholder image area */}
      <div className={isIndustrial
        ? "mb-4 aspect-square w-full overflow-hidden bg-gray-100 flex items-center justify-center text-gray-300"
        : "mb-4 aspect-square w-full overflow-hidden rounded-lg bg-gray-100 flex items-center justify-center text-gray-300"}>
        {productImage ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={productImage}
            alt={product.product_name}
            className="h-full w-full object-cover"
          />
        ) : (
          <svg className="h-12 w-12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
          </svg>
        )}
      </div>
      <p className={isIndustrial
        ? "mb-1 text-[11px] font-black uppercase tracking-[0.16em] text-primary"
        : "text-xs font-mono text-gray-400 mb-1"}>{product.model_number}</p>
      <h3 className={isIndustrial
        ? "text-sm font-black uppercase tracking-wide text-gray-900 group-hover:text-primary transition-colors line-clamp-2"
        : "text-sm font-semibold text-gray-800 group-hover:text-blue-700 transition-colors line-clamp-2"}>
        {product.product_name}
      </h3>
      <p className="mt-2 text-xs text-gray-500 line-clamp-2">{product.short_description}</p>
    </Link>
  );
}
