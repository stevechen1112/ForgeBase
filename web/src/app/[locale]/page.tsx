import Link from "next/link";
import type { Metadata } from "next";
import {
  getPublishedCategories,
  getPublishedApplications,
  getPublishedCertifications,
  getFeaturedProducts,
} from "@/lib/api";
import { ApplicationCard } from "@/components/ui/ApplicationCard";
import { CertificationBadge } from "@/components/ui/CertificationBadge";
import { ChatWidget } from "@/components/chat/ChatWidget";
import { StructuredData, buildOrganizationSchema } from "@/components/seo/StructuredData";
import { PageViewTracker } from "@/components/tracking/PageViewTracker";
import { HOME_HERO_IMAGE, getCategoryCardImage, getProductImage } from "@/lib/demoAssets";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "https://example.com";
const SITE_NAME = process.env.NEXT_PUBLIC_SITE_NAME === "ForgeBase"
  ? "NorthForge Tools"
  : (process.env.NEXT_PUBLIC_SITE_NAME || "NorthForge Tools");

const WHY_US_ICONS = [
  (
    <svg key="repeat-orders" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  ),
  (
    <svg key="oem-private-label" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M6.115 5.19l.319 1.913A6 6 0 008.11 10.36L9.75 12l-.387.775c-.217.433-.132.956.21 1.298l1.348 1.348c.21.21.329.497.329.795v1.089c0 .426.24.815.622 1.006l.153.076c.433.217.956.132 1.298-.21l.723-.723a8.7 8.7 0 002.288-4.042 1.087 1.087 0 00-.358-1.099l-1.33-1.108c-.251-.21-.582-.299-.905-.245l-1.17.195a1.125 1.125 0 01-.98-.314l-.295-.295a1.125 1.125 0 010-1.591l.017-.017c.372-.372.596-.878.596-1.414 0-.523-.199-1.026-.554-1.403L9.62 5.498a1.875 1.875 0 00-2.346-.271l-1.16.58z" />
    </svg>
  ),
  (
    <svg key="documentation" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M11.42 15.17L17.25 21A2.652 2.652 0 0021 17.25l-5.877-5.877M11.42 15.17l2.496-3.03c.317-.384.74-.626 1.208-.766M11.42 15.17l-4.655 5.653a2.548 2.548 0 11-3.586-3.586l6.837-5.63m5.108-.233c.55-.164 1.163-.188 1.743-.14a4.5 4.5 0 004.486-6.336l-3.276 3.277a3.004 3.004 0 01-2.25-2.25l3.276-3.276a4.5 4.5 0 00-6.336 4.486c.091 1.076-.071 2.264-.904 2.95l-.102.085m-1.745 1.437L5.909 7.5H4.5L2.25 3.75l1.5-1.5L7.5 4.5v1.409l4.26 4.26m-1.745 1.437l1.745-1.437m6.615 8.206L15.75 15.75M4.867 19.125h.008v.008h-.008v-.008z" />
    </svg>
  ),
  (
    <svg key="mixed-sku" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" />
    </svg>
  ),
  (
    <svg key="product-scope" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  ),
  (
    <svg key="compliance" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v12m-3-2.818l.879.659c1.171.879 3.07.879 4.242 0 1.172-.879 1.172-2.303 0-3.182C13.536 12.219 12.768 12 12 12c-.725 0-1.45-.22-2.003-.659-1.106-.879-1.106-2.303 0-3.182s2.9-.879 4.006 0l.415.33M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  ),
];

const HOME_PAGE_COPY = {
  en: {
    metadata: {
      title: "NorthForge Tools | OEM Hand Tool Manufacturer in Taiwan",
      description:
        "Taiwan-based OEM/ODM hand tool manufacturer specializing in torque tools, insulated tools, workshop tools, and private-label toolkit programs for distributors and tool brands.",
    },
    hero: {
      eyebrow: "Trusted Export Manufacturer for Professional Tool Programs",
      titleLine1: "Precision-Built Hand Tools for Brands,",
      titleLine2: "Distributors, and Industrial Buyers",
      description: "NorthForge Tools helps importers, private-label brands, and industrial distributors source torque tools, insulated tools, workshop tools, and custom toolkit programs with stronger quality control and cleaner export execution.",
      primaryCta: "Request a Quote",
      secondaryCta: "Browse Products →",
    },
    stats: [
      { value: "20+", label: "Years Export Experience" },
      { value: "30+", label: "Core Demo SKUs" },
      { value: "40+", label: "Countries Served" },
      { value: "98%", label: "Shipment-Readiness KPI" },
    ],
    featured: {
      eyebrow: "Featured",
      title: "Selected Tool Lines",
      description: "Representative SKUs across torque, insulated, workshop, automotive service, and toolkit programs.",
      cardCta: "View Details →",
      sectionCta: "Browse All Products",
    },
    catalogue: {
      eyebrow: "Our Catalogue",
      title: "Product Categories",
      description: "Browse the core families NorthForge builds for distributor programs, private-label launches, and industrial buying teams.",
      sectionCta: "View Full Catalogue",
    },
    why: {
      eyebrow: "Why NorthForge",
      title: "Built for Global Buyers",
      description: "Everything we do is designed to make your sourcing simpler, safer, and more profitable.",
      items: [
        {
          title: "Stable Repeat Orders",
          desc: "NorthForge reduces drift between approved samples and recurring production through tighter drawing control, verification workflow, and packaging discipline.",
        },
        {
          title: "OEM and Private Label Execution",
          desc: "From logo application and insert cards to barcode labels and retail-ready assortments, NorthForge supports programs that need more than loose tools in cartons.",
        },
        {
          title: "Documentation Discipline",
          desc: "Export buyers need clean packing lists, carton marks, barcode accuracy, and compliance-support paperwork. NorthForge treats those details as part of the product program.",
        },
        {
          title: "Mixed-SKU Program Flexibility",
          desc: "The team is structured to support recurring mixed-SKU programs, toolkit builds, and distributor-ready assortments without enterprise-scale complexity.",
        },
        {
          title: "Tool-Focused Product Scope",
          desc: "The catalog is built around torque tools, insulated tools, workshop tools, automotive service tools, and custom toolkit programs for professional channels.",
        },
        {
          title: "Compliance-Support Ready",
          desc: "NorthForge supports ISO 9001 workflow, insulated-tool process discipline, RoHS and REACH documentation, and third-party inspection coordination when needed.",
        },
      ],
    },
    applications: {
      eyebrow: "Industries",
      title: "Featured Applications",
      description: "NorthForge focuses on programs where repeatability, packaging control, and clean documentation matter as much as the tool itself.",
      sectionCta: "View all industries →",
    },
    oem: {
      eyebrow: "OEM / ODM Flow",
      title: "How a Tool Program Moves Forward",
      description: "The process is designed to keep product, packaging, and shipment execution aligned from the first discussion through recurring orders.",
      steps: [
        {
          title: "Define Product Scope",
          desc: "Clarify target market, usage scenario, and whether a standard catalog item or customization path makes more commercial sense.",
        },
        {
          title: "Review Branding and Packaging",
          desc: "Confirm logo application, insert cards, molded cases, barcode labels, and carton marking requirements before sampling.",
        },
        {
          title: "Approve Samples and Key Specs",
          desc: "Lock in critical details such as torque range, insulation class, hardness targets, finish, packaging format, and inspection points.",
        },
        {
          title: "Move into Controlled Production",
          desc: "Production, packing, export documentation, and shipment readiness are managed as one workflow so the program stays consistent after approval.",
        },
      ],
    },
    certifications: {
      eyebrow: "Quality Assurance",
      title: "Certifications & Standards",
      description: "Compliance support is positioned as a working part of export execution, not a footer claim added after the tooling is done.",
      sectionCta: "View all certifications →",
    },
    finalCta: {
      title: "Build a Cleaner, More Reliable Tool Program",
      description: "Whether you need recurring catalog supply, private-label packaging, or a custom toolkit assortment, NorthForge can help structure the right sourcing program for your market.",
      primaryCta: "Request a Quote",
      secondaryCta: "Contact Sales",
      note: "Response within 1 business day for qualified enquiries",
    },
  },
  "zh-TW": {
    metadata: {
      title: "NorthForge Tools | 台灣 OEM 手工具製造商",
      description:
        "台灣 OEM/ODM 手工具製造商，專注於扭力工具、絕緣工具、工坊工具與客製工具組方案，服務經銷商與工具品牌。",
    },
    hero: {
      eyebrow: "專為專業工具專案打造的出口製造夥伴",
      titleLine1: "為品牌商、經銷商與工業買家打造",
      titleLine2: "高一致性的專業手工具方案",
      description: "NorthForge Tools 協助進口商、自有品牌與工業通路採購扭力工具、絕緣工具、工坊工具與客製工具組，以更穩定的品質控管與更乾淨的出口流程推進專案。",
      primaryCta: "立即詢價",
      secondaryCta: "瀏覽產品 →",
    },
    stats: [
      { value: "20+", label: "年出口經驗" },
      { value: "30+", label: "核心示範 SKU" },
      { value: "40+", label: "服務國家數" },
      { value: "98%", label: "出貨就緒 KPI" },
    ],
    featured: {
      eyebrow: "精選系列",
      title: "代表性工具產品線",
      description: "涵蓋扭力、絕緣、工坊、汽修與工具組方案的代表型號。",
      cardCta: "查看詳情 →",
      sectionCta: "瀏覽全部產品",
    },
    catalogue: {
      eyebrow: "產品目錄",
      title: "產品分類",
      description: "瀏覽 NorthForge 為經銷專案、自有品牌上市與工業採購團隊打造的核心產品家族。",
      sectionCta: "查看完整目錄",
    },
    why: {
      eyebrow: "選擇 NorthForge 的理由",
      title: "為全球採購團隊而設計",
      description: "我們的流程設計目標，就是讓你的採購更簡單、更穩定，也更容易持續獲利。",
      items: [
        {
          title: "穩定的重複下單品質",
          desc: "NorthForge 透過更嚴謹的圖面控管、驗證流程與包裝紀律，降低核樣後量產與後續補單之間的落差。",
        },
        {
          title: "OEM 與自有品牌執行能力",
          desc: "從 Logo 呈現、內頁卡、條碼標籤到零售型組套，NorthForge 支援的不只是散裝工具出貨。",
        },
        {
          title: "文件與出口細節紀律",
          desc: "出口買家需要乾淨的裝箱單、外箱標示、條碼準確性與合規支援文件；NorthForge 將這些視為產品專案的一部分。",
        },
        {
          title: "混 SKU 專案彈性",
          desc: "團隊可支援持續性的混 SKU 專案、工具組建置與經銷通路組套，不必用企業級複雜度去換取執行能力。",
        },
        {
          title: "聚焦手工具產品範圍",
          desc: "產品架構聚焦於扭力工具、絕緣工具、工坊工具、汽修工具與客製工具組，對應專業通路與出口市場。",
        },
        {
          title: "可支援合規導向專案",
          desc: "NorthForge 可支援 ISO 9001 流程、絕緣工具製程紀律、RoHS/REACH 文件整理，以及第三方驗貨協調。",
        },
      ],
    },
    applications: {
      eyebrow: "應用場景",
      title: "重點應用領域",
      description: "NorthForge 聚焦在那些對一致性、包裝控管與文件完整度同樣重視的工具專案。",
      sectionCta: "查看全部應用場景 →",
    },
    oem: {
      eyebrow: "OEM / ODM 流程",
      title: "一個工具專案如何穩定推進",
      description: "這套流程的目的是從首次討論到持續補單，都讓產品、包裝與出貨執行維持一致。",
      steps: [
        {
          title: "定義產品範圍",
          desc: "先釐清目標市場、使用情境，以及該選擇標準品還是客製化方案，哪一條路更具商業效率。",
        },
        {
          title: "確認品牌與包裝需求",
          desc: "在打樣前確認 Logo 呈現、內頁卡、塑盒、條碼標籤與外箱標示需求。",
        },
        {
          title: "核樣與鎖定關鍵規格",
          desc: "把扭力範圍、絕緣等級、硬度目標、表面處理、包裝形式與檢驗重點一次鎖定。",
        },
        {
          title: "進入受控量產",
          desc: "量產、包裝、出口文件與出貨準備作為同一套工作流管理，確保核樣後的專案一致性。",
        },
      ],
    },
    certifications: {
      eyebrow: "品質與驗證",
      title: "認證與標準",
      description: "合規支援在這裡不是收尾補上的行銷話術，而是出口執行流程中的實際工作項目。",
      sectionCta: "查看全部認證 →",
    },
    finalCta: {
      title: "建立更乾淨、更穩定的工具供應方案",
      description: "不論你需要持續型目錄供貨、自有品牌包裝，或客製化工具組方案，NorthForge 都能協助你為目標市場建立更合適的採購模式。",
      primaryCta: "立即詢價",
      secondaryCta: "聯絡業務",
      note: "合格詢問可於 1 個工作天內回覆",
    },
  },
} as const;

export async function generateMetadata({ params }: { params: Promise<{ locale: string }> }): Promise<Metadata> {
  const { locale } = await params;
  const copy = HOME_PAGE_COPY[locale as keyof typeof HOME_PAGE_COPY] ?? HOME_PAGE_COPY.en;
  return {
    title: copy.metadata.title,
    description: copy.metadata.description,
  };
}

export default async function HomePage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  const copy = HOME_PAGE_COPY[locale as keyof typeof HOME_PAGE_COPY] ?? HOME_PAGE_COPY.en;
  const [categories, applicationsRes, certifications, featuredProducts] = await Promise.all([
    getPublishedCategories(locale),
    getPublishedApplications(locale),
    getPublishedCertifications(locale),
    getFeaturedProducts(locale),
  ]);
  const applications = applicationsRes.data.slice(0, 6);
  const categorySlugById = new Map(categories.map((category) => [category.id, category.slug]));

  return (
    <>
      <PageViewTracker pageType="home" />
      <ChatWidget contextPage="/" contextEntityType="home" />
      <StructuredData
        data={buildOrganizationSchema({ name: SITE_NAME, url: SITE_URL })}
      />

      {/* ── Hero ── */}
      <section className="relative overflow-hidden bg-blue-950 text-white">
        <div
          className="absolute inset-0 bg-cover bg-center"
          style={{ backgroundImage: `url(${HOME_HERO_IMAGE})` }}
        />
        <div className="absolute inset-0 bg-gradient-to-r from-slate-950/90 via-blue-950/80 to-blue-900/55" />
        {/* Background grid pattern */}
        <div
          className="pointer-events-none absolute inset-0 opacity-10"
          style={{
            backgroundImage:
              "linear-gradient(white 1px, transparent 1px), linear-gradient(90deg, white 1px, transparent 1px)",
            backgroundSize: "40px 40px",
          }}
        />
        <div className="relative mx-auto max-w-6xl px-6 py-28 sm:py-36">
          <div className="flex flex-col items-center text-center">
            {/* Eyebrow */}
            <span className="mb-5 inline-flex items-center gap-2 rounded-full border border-blue-400/30 bg-blue-800/40 px-4 py-1.5 text-xs font-semibold uppercase tracking-widest text-blue-200">
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-green-400" />
              {copy.hero.eyebrow}
            </span>

            <h1 className="max-w-4xl text-4xl font-extrabold leading-tight tracking-tight sm:text-5xl lg:text-6xl">
              {copy.hero.titleLine1}
              <br />
              <span className="text-blue-300">{copy.hero.titleLine2}</span>
            </h1>

            <p className="mx-auto mt-5 max-w-3xl text-lg leading-relaxed text-blue-100">
              {copy.hero.description}
            </p>

            <div className="mt-9 flex flex-col items-center gap-4 sm:flex-row sm:justify-center">
              <Link
                href="/rfq"
                className="rounded-xl bg-white px-8 py-3.5 text-sm font-bold text-blue-900 shadow-lg hover:bg-blue-50 transition-colors"
              >
                {copy.hero.primaryCta}
              </Link>
              <Link
                href="/products"
                className="rounded-xl border border-white/30 bg-white/10 px-8 py-3.5 text-sm font-semibold text-white hover:bg-white/20 transition-colors"
              >
                {copy.hero.secondaryCta}
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* ── Trust bar / Stats ── */}
      <section className="border-b border-gray-100 bg-white">
        <div className="mx-auto max-w-6xl px-6 py-10">
          <div className="grid grid-cols-2 gap-6 sm:grid-cols-4">
            {copy.stats.map((s) => (
              <div key={s.label} className="flex flex-col items-center text-center">
                <span className="text-3xl font-extrabold text-blue-700">{s.value}</span>
                <span className="mt-1 text-sm text-gray-500">{s.label}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Featured Products ── */}
      {featuredProducts.length > 0 && (
        <section className="bg-white py-20">
          <div className="mx-auto max-w-6xl px-6">
            <div className="text-center">
              <span className="text-xs font-semibold uppercase tracking-widest text-blue-600">
                {copy.featured.eyebrow}
              </span>
              <h2 className="mt-2 text-3xl font-bold text-gray-900">{copy.featured.title}</h2>
              <p className="mx-auto mt-3 max-w-2xl text-base text-gray-500">
                {copy.featured.description}
              </p>
            </div>

            <div className="mt-12 grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
              {featuredProducts.map((product) => (
                <Link
                  key={product.id}
                  href={categorySlugById.get(product.category_id) ? `/products/${categorySlugById.get(product.category_id)}/${product.slug}` : "/products"}
                  className="group flex flex-col rounded-xl border border-gray-200 bg-white p-5 shadow-sm hover:border-blue-300 hover:shadow-md transition-all"
                >
                  <div className="mb-3 h-32 w-full overflow-hidden rounded-lg bg-blue-50">
                    {getProductImage(product, categorySlugById.get(product.category_id)) ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img
                        src={getProductImage(product, categorySlugById.get(product.category_id)) ?? undefined}
                        alt={product.product_name}
                        className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
                      />
                    ) : (
                      <div className="flex h-full items-center justify-center text-4xl text-blue-300 group-hover:bg-blue-100 transition-colors">
                        ⬡
                      </div>
                    )}
                  </div>
                  <h3 className="text-sm font-semibold text-gray-900 group-hover:text-blue-700 transition-colors">
                    {product.product_name}
                  </h3>
                  <p className="mt-1 text-xs text-gray-500">{product.model_number}</p>
                  <p className="mt-2 line-clamp-2 text-xs leading-relaxed text-gray-500">
                    {product.short_description}
                  </p>
                  <span className="mt-3 text-xs font-semibold text-blue-600 group-hover:underline">
                    {copy.featured.cardCta}
                  </span>
                </Link>
              ))}
            </div>

            <div className="mt-10 text-center">
              <Link
                href="/products"
                className="inline-flex items-center gap-1 rounded-lg border border-blue-200 bg-white px-6 py-2.5 text-sm font-semibold text-blue-700 hover:bg-blue-50 transition-colors"
              >
                {copy.featured.sectionCta}
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
                </svg>
              </Link>
            </div>
          </div>
        </section>
      )}

      {/* ── Product Categories ── */}
      {categories.length > 0 && (
        <section className="bg-gray-50 py-20">
          <div className="mx-auto max-w-6xl px-6">
            <div className="text-center">
              <span className="text-xs font-semibold uppercase tracking-widest text-blue-600">
                {copy.catalogue.eyebrow}
              </span>
              <h2 className="mt-2 text-3xl font-bold text-gray-900">{copy.catalogue.title}</h2>
              <p className="mx-auto mt-3 max-w-2xl text-base text-gray-500">
                {copy.catalogue.description}
              </p>
            </div>

            <div className="mt-12 grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
              {categories.map((cat) => (
                <Link
                  key={cat.id}
                  href={`/products/${cat.slug}`}
                  className="group flex flex-col items-center rounded-xl border border-gray-200 bg-white p-6 text-center shadow-sm hover:border-blue-300 hover:shadow-md transition-all"
                >
                  {getCategoryCardImage(cat) ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={getCategoryCardImage(cat) ?? undefined}
                      alt={cat.category_name}
                      className="mb-3 h-20 w-full rounded-lg object-cover"
                    />
                  ) : (
                    <span className="mb-3 flex h-20 w-full items-center justify-center rounded-lg bg-blue-50 text-3xl group-hover:bg-blue-100 transition-colors">
                      ⬡
                    </span>
                  )}
                  <span className="text-sm font-semibold text-gray-800 group-hover:text-blue-700 transition-colors">
                    {cat.category_name}
                  </span>
                </Link>
              ))}
            </div>

            <div className="mt-10 text-center">
              <Link
                href="/products"
                className="inline-flex items-center gap-1 rounded-lg border border-blue-200 bg-white px-6 py-2.5 text-sm font-semibold text-blue-700 hover:bg-blue-50 transition-colors"
              >
                {copy.catalogue.sectionCta}
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
                </svg>
              </Link>
            </div>
          </div>
        </section>
      )}

      {/* ── Why Choose Us ── */}
      <section className="bg-white py-20">
        <div className="mx-auto max-w-6xl px-6">
          <div className="text-center">
            <span className="text-xs font-semibold uppercase tracking-widest text-blue-600">
              {copy.why.eyebrow}
            </span>
            <h2 className="mt-2 text-3xl font-bold text-gray-900">{copy.why.title}</h2>
            <p className="mx-auto mt-3 max-w-xl text-base text-gray-500">
              {copy.why.description}
            </p>
          </div>

          <div className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {copy.why.items.map((item, index) => (
              <div
                key={item.title}
                className="rounded-xl border border-gray-100 bg-gray-50 p-6 hover:border-blue-200 hover:bg-blue-50/30 transition-colors"
              >
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-100 text-blue-700">
                  {WHY_US_ICONS[index]}
                </div>
                <h3 className="mt-4 text-base font-semibold text-gray-900">{item.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-gray-500">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Applications ── */}
      {applications.length > 0 && (
        <section className="bg-gray-50 py-20">
          <div className="mx-auto max-w-6xl px-6">
            <div className="text-center">
              <span className="text-xs font-semibold uppercase tracking-widest text-blue-600">
                {copy.applications.eyebrow}
              </span>
              <h2 className="mt-2 text-3xl font-bold text-gray-900">{copy.applications.title}</h2>
              <p className="mx-auto mt-3 max-w-2xl text-base text-gray-500">
                {copy.applications.description}
              </p>
            </div>

            <div className="mt-12 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
              {applications.map((app) => (
                <ApplicationCard key={app.id} application={app} />
              ))}
            </div>

            <div className="mt-10 text-center">
              <Link
                href="/applications"
                className="inline-flex items-center gap-1 text-sm font-semibold text-blue-700 hover:underline"
              >
                {copy.applications.sectionCta}
              </Link>
            </div>
          </div>
        </section>
      )}

      {/* ── OEM / ODM flow ── */}
      <section className="bg-white py-20">
        <div className="mx-auto max-w-6xl px-6">
          <div className="text-center">
            <span className="text-xs font-semibold uppercase tracking-widest text-blue-600">
              {copy.oem.eyebrow}
            </span>
            <h2 className="mt-2 text-3xl font-bold text-gray-900">{copy.oem.title}</h2>
            <p className="mx-auto mt-3 max-w-2xl text-base text-gray-500">
              {copy.oem.description}
            </p>
          </div>

          <div className="mt-12 grid gap-6 md:grid-cols-2 xl:grid-cols-4">
            {copy.oem.steps.map((step, index) => (
              <div key={step.title} className="rounded-xl border border-gray-100 bg-gray-50 p-6">
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-blue-700 text-sm font-bold text-white">
                  0{index + 1}
                </div>
                <h3 className="mt-4 text-base font-semibold text-gray-900">{step.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-gray-600">{step.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Certifications ── */}
      {certifications.length > 0 && (
        <section className="bg-gray-50 py-20">
          <div className="mx-auto max-w-6xl px-6">
            <div className="text-center">
              <span className="text-xs font-semibold uppercase tracking-widest text-blue-600">
                {copy.certifications.eyebrow}
              </span>
              <h2 className="mt-2 text-3xl font-bold text-gray-900">{copy.certifications.title}</h2>
              <p className="mx-auto mt-3 max-w-2xl text-base text-gray-500">
                {copy.certifications.description}
              </p>
            </div>

            <div className="mt-12 grid grid-cols-2 gap-5 sm:grid-cols-3 lg:grid-cols-4">
              {certifications.map((cert) => (
                <CertificationBadge key={cert.id} certification={cert} />
              ))}
            </div>

            <div className="mt-10 text-center">
              <Link
                href="/certifications"
                className="inline-flex items-center gap-1 text-sm font-semibold text-blue-700 hover:underline"
              >
                {copy.certifications.sectionCta}
              </Link>
            </div>
          </div>
        </section>
      )}

      {/* ── CTA Banner ── */}
      <section className="bg-blue-900 py-20 text-white">
        <div className="mx-auto max-w-4xl px-6 text-center">
          <h2 className="text-3xl font-bold">{copy.finalCta.title}</h2>
          <p className="mx-auto mt-4 max-w-xl text-lg text-blue-200 leading-relaxed">
            {copy.finalCta.description}
          </p>
          <div className="mt-8 flex flex-col items-center gap-4 sm:flex-row sm:justify-center">
            <Link
              href="/rfq"
              className="rounded-xl bg-white px-8 py-3.5 text-sm font-bold text-blue-900 shadow-lg hover:bg-blue-50 transition-colors"
            >
              {copy.finalCta.primaryCta}
            </Link>
            <Link
              href="/contact"
              className="rounded-xl border border-white/30 bg-white/10 px-8 py-3.5 text-sm font-semibold text-white hover:bg-white/20 transition-colors"
            >
              {copy.finalCta.secondaryCta}
            </Link>
          </div>
          <p className="mt-6 text-xs text-blue-400">
            {copy.finalCta.note}
          </p>
        </div>
      </section>
    </>
  );
}
