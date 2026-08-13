/**
 * Renders a JSON-LD structured data script tag.
 * Usage: <StructuredData data={{ "@context": "https://schema.org", ... }} />
 */
type Props = { data: Record<string, unknown> };

export function StructuredData({ data }: Props) {
  return (
    <script
      type="application/ld+json"
      // Using dangerouslySetInnerHTML is intentional and safe here because
      // `data` comes from our own trusted API (not user input).
      dangerouslySetInnerHTML={{ __html: JSON.stringify(data) }}
    />
  );
}

/** Helper builders ---------------------------------------------------------- */

export function buildProductSchema(opts: {
  name: string;
  description?: string;
  model?: string;      // model_number → used for mpn
  brand?: string;
  imageUrl?: string;
  imageAlt?: string;
  url: string;
  // 2.3.3 extended fields
  specs?: Record<string, string>;
  certifications?: Array<{ cert_name: string; issuing_body?: string | null }>;
  alternatives?: Array<{ product_name: string; model_number?: string | null; slug: string; categorySlug?: string }>;
  siteUrl?: string;
  /** Whether the product is in stock. Defaults to true. */
  inStock?: boolean;
}) {
  // Build additionalProperty: specs first, then certifications
  const additionalProperty: Record<string, unknown>[] = [];
  if (opts.specs) {
    for (const [name, value] of Object.entries(opts.specs)) {
      additionalProperty.push({ "@type": "PropertyValue", name, value: String(value) });
    }
  }
  if (opts.certifications?.length) {
    for (const cert of opts.certifications) {
      additionalProperty.push({
        "@type": "PropertyValue",
        name: "Certification",
        value: cert.issuing_body
          ? `${cert.cert_name} (${cert.issuing_body})`
          : cert.cert_name,
      });
    }
  }

  const isSimilarTo = opts.alternatives?.map((alt) => ({
    "@type": "Product",
    name: alt.product_name,
    mpn: alt.model_number ?? undefined,
    url:
      opts.siteUrl && alt.categorySlug
        ? `${opts.siteUrl}/products/${alt.categorySlug}/${alt.slug}`
        : undefined,
  }));

  return {
    "@context": "https://schema.org",
    "@type": "Product",
    name: opts.name,
    description: opts.description,
    mpn: opts.model,
    brand: opts.brand ? { "@type": "Brand", name: opts.brand } : undefined,
    image: opts.imageUrl
      ? [{ "@type": "ImageObject", url: opts.imageUrl, description: opts.imageAlt ?? opts.name }]
      : undefined,
    url: opts.url,
    offers: {
      "@type": "Offer",
      url: opts.url,
      availability: (opts.inStock ?? true)
        ? "https://schema.org/InStock"
        : "https://schema.org/OutOfStock",
      priceCurrency: "USD",
      priceSpecification: {
        "@type": "PriceSpecification",
        description: "Contact for quotation",
      },
      seller: opts.brand ? { "@type": "Organization", name: opts.brand } : undefined,
    },
    additionalProperty: additionalProperty.length > 0 ? additionalProperty : undefined,
    isSimilarTo: isSimilarTo?.length ? isSimilarTo : undefined,
  };
}

export function buildBreadcrumbSchema(
  items: Array<{ name: string; url: string }>
) {
  return {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: items.map((item, idx) => ({
      "@type": "ListItem",
      position: idx + 1,
      name: item.name,
      item: item.url,
    })),
  };
}

export function buildFAQSchema(items: Array<{ question: string; answer: string }>) {
  return {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    mainEntity: items.map((faq) => ({
      "@type": "Question",
      name: faq.question,
      acceptedAnswer: { "@type": "Answer", text: faq.answer },
    })),
  };
}

export function buildOrganizationSchema(opts: {
  name: string;
  url: string;
  logoUrl?: string;
  sameAs?: string[];
}) {
  return {
    "@context": "https://schema.org",
    "@type": "Organization",
    name: opts.name,
    url: opts.url,
    logo: opts.logoUrl ? { "@type": "ImageObject", url: opts.logoUrl } : undefined,
    sameAs: opts.sameAs,
  };
}
