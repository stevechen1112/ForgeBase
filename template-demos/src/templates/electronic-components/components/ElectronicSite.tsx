import Image from "next/image";
import Link from "next/link";
import { ArrowRight, BookOpen, Box, Check, ChevronRight, CircuitBoard, FileCheck2, FileText, FlaskConical, Menu, PackageSearch, Search, ShieldCheck, Zap } from "lucide-react";
import { DemoCTA } from "@/components/DemoCTA";
import { DemoNotice } from "@/components/DemoNotice";
import type { TemplateProduct } from "@/contracts/forgebase";
import { electronicComponentsData as data, electronicsAvailability, electronicsBase, electronicsResources } from "../data";
import styles from "./Electronics.module.css";
import { ParametricCatalog } from "./ParametricCatalog";
import { SampleRequest } from "./SampleRequest";

const images = {
  family: `${electronicsBase}/component-family-hero.png`,
  connector: `${electronicsBase}/mezzanine-connector-macro.png`,
  protection: `${electronicsBase}/protection-device-reel.png`,
  lab: `${electronicsBase}/component-validation-lab.png`,
};

const categoryImages: Record<string, string> = {
  "cat-connectors": images.connector,
  "cat-protection": images.protection,
  "cat-sensors": images.family,
};

function cta(id: string) { return data.ctas.find((item) => item.id === id)!; }

const navigation = [
  { label: "Products", href: `${electronicsBase}/products/` },
  { label: "Applications", href: `${electronicsBase}/applications/` },
  { label: "Quality", href: `${electronicsBase}/certifications/` },
  { label: "Resources", href: `${electronicsBase}/resources/` },
  { label: "Company", href: `${electronicsBase}/about/` },
];

function Brand() {
  return <Link href={`${electronicsBase}/`} className={styles.brand} aria-label="Veltrix Components demo home"><span className={styles.brandIcon}><CircuitBoard /></span><span>VELTRIX<small>COMPONENTS / DEMO</small></span></Link>;
}

function SiteSearch() {
  return <Link href={`${electronicsBase}/products/`} className={styles.siteSearch}><Search size={18} /><span>Search part number or parameter</span><kbd>⌘ K</kbd></Link>;
}

export function ElectronicsShell({ children }: { children: React.ReactNode }) {
  return <main className={styles.site}>
    <DemoNotice message="本頁為電子零組件示意型錄；所有料號、規格、庫存、合規及文件皆為假資料，也不傳送申請。" />
    <div className={styles.utility}><span>Engineering catalogue / Demo dataset</span><div><span>Region: Global Demo</span><span>Language: EN</span><Link href="/">Template Lab</Link></div></div>
    <header className={styles.header}><Brand /><SiteSearch /><DemoCTA cta={cta("electronics-nav-sample")} className={styles.headerCta}>Samples <Box size={17} /></DemoCTA><details className={styles.mobileNav}><summary aria-label="Open component catalogue navigation"><Menu /></summary><nav>{navigation.map((item) => <Link key={item.href} href={item.href}>{item.label}</Link>)}<DemoCTA cta={cta("electronics-nav-sample")}>Request samples</DemoCTA></nav></details></header>
    <nav className={styles.categoryNav} aria-label="Component catalogue navigation"><div>{navigation.map((item) => <Link key={item.href} href={item.href}>{item.label}</Link>)}</div><span>3 Demo families · 3 Demo parts</span></nav>
    {children}
    <footer className={styles.footer}><div><Brand /><p>{data.site.disclosure.message}</p></div><div><h2>Catalogue</h2><Link href={`${electronicsBase}/products/`}>All parts</Link><Link href={`${electronicsBase}/resources/`}>Technical resources</Link><DemoCTA cta={cta("electronics-nav-sample")}>Sample request</DemoCTA></div><div><h2>Demo limits</h2><p>{data.site.legalNotice}. No orderable inventory, qualification or compliance status is claimed.</p></div></footer>
  </main>;
}

function CategoryTile({ categoryId, index }: { categoryId: string; index: number }) {
  const category = data.categories.find((item) => item.id === categoryId)!;
  const count = data.products.filter((product) => product.categoryId === categoryId).length;
  return <Link href={`${electronicsBase}/categories/${category.slug}/`} className={styles.categoryTile}><span>0{index + 1}</span><div><b>{category.name}</b><small>{count} Demo part</small></div><ChevronRight size={16} /></Link>;
}

export function ElectronicComponentsTemplate() {
  return <ElectronicsShell>
    <section className={styles.catalogHero}>
      <div className={styles.heroHeading}><span>PARAMETRIC DISCOVERY</span><h1>Find the right part faster.</h1><p>{data.site.tagline}</p><div><DemoCTA cta={cta("electronics-browse")} className={styles.primaryButton}>Search the catalogue <ArrowRight /></DemoCTA><DemoCTA cta={cta("electronics-datasheet")} className={styles.textButton}>Demo datasheets <FileText size={16} /></DemoCTA></div></div>
      <div className={styles.categoryIndex}><header><span>PRODUCT FAMILIES</span><b>03</b></header>{data.categories.map((category, index) => <CategoryTile key={category.id} categoryId={category.id} index={index} />)}</div>
      <div className={styles.heroProduct}><Image src={images.family} alt="Fictional family of electronic connectors, protection devices and sensors arranged for an engineering catalogue" fill loading="eager" sizes="(max-width: 800px) 100vw, 52vw" /><span>COMPONENT FAMILY / ILLUSTRATIVE</span></div>
      <aside className={styles.availabilityCard}><header><span>DEMO AVAILABILITY</span><i /></header>{electronicsAvailability.map((item) => <div key={item.part}><b>{item.part}</b><span>{item.status}</span><small>{item.lead}</small></div>)}<DemoCTA cta={cta("electronics-nav-sample")}>Open sample cart <ArrowRight size={16} /></DemoCTA></aside>
    </section>
    <section className={styles.catalogSection}><div className={styles.sectionIntro}><div><span>PART FINDER / 01</span><h2>Filter specifications, not marketing claims.</h2></div><p>Searchable attributes, consistent units and comparison states demonstrate how normalized ForgeBase product data can support engineering selection.</p></div><ParametricCatalog products={data.products} categories={data.categories} embedded /></section>
    <section className={styles.applicationStrip}>{data.applications.map((application, index) => <article key={application.id}><span>0{index + 1}</span>{index === 0 ? <CircuitBoard /> : index === 1 ? <Zap /> : <PackageSearch />}<h2>{application.name}</h2><p>{application.description}</p></article>)}<div className={styles.applicationAction}><span>DESIGN CONTEXT</span><h2>Start from the circuit problem.</h2><DemoCTA cta={cta("electronics-application")}>Explore applications <ArrowRight size={17} /></DemoCTA></div></section>
    <section className={styles.qualityFeature}><div className={styles.qualityImage}><Image src={images.lab} alt="Electronics validation engineer testing a fictional sensor PCB at a laboratory bench" fill sizes="(max-width: 800px) 100vw, 52vw" /></div><div className={styles.qualityCopy}><span>QUALITY EVIDENCE / 02</span><h2>Connect every claim to a record.</h2><p>The template separates electrical data, qualification evidence and regulatory documentation, while clearly marking every Demo record as illustrative.</p><ul><li><Check />Revision-aware technical documents</li><li><Check />Explicit Demo compliance status</li><li><Check />Product-to-evidence mapping</li></ul><DemoCTA cta={cta("electronics-quality")}>Review quality framework <ArrowRight size={17} /></DemoCTA></div></section>
  </ElectronicsShell>;
}

function PageHeader({ eyebrow, title, description }: { eyebrow: string; title: string; description: string }) {
  return <header className={styles.pageHeader}><span>{eyebrow}</span><h1>{title}</h1><p>{description}</p></header>;
}

export function ElectronicsProductsPage() {
  return <ElectronicsShell><PageHeader eyebrow="ALL PARTS / 01" title="Parametric component catalogue" description="Filter fictional parts by number, family, package and electrical attributes; select up to three records for comparison." /><ParametricCatalog products={data.products} categories={data.categories} /></ElectronicsShell>;
}

export function ElectronicsProductPage({ product }: { product: TemplateProduct }) {
  const category = data.categories.find((item) => item.id === product.categoryId)!;
  return <ElectronicsShell><div className={styles.breadcrumbs}><Link href={`${electronicsBase}/products/`}>All parts</Link><ChevronRight size={14} /><span>{category.name}</span><ChevronRight size={14} /><b>{product.modelNumber}</b></div><section className={styles.productHero}><div className={styles.productImage}><Image src={categoryImages[product.categoryId ?? ""]} alt={`Fictional technical product image representing ${product.name}`} fill loading="eager" sizes="(max-width: 800px) 100vw, 42vw" /><span>DEMO PRODUCT IMAGE</span></div><div className={styles.productSummary}><span>{category.name}</span><h1>{product.modelNumber}</h1><h2>{product.name}</h2><p>{product.shortDescription}</p><div className={styles.productActions}><DemoCTA cta={{ id: `${product.id}-sample`, label: "Add to sample request", href: `${electronicsBase}/rfq/`, intent: "request_sample" }} className={styles.primaryButton}>Add to sample request <Box size={17} /></DemoCTA><DemoCTA cta={cta("electronics-datasheet")} className={styles.secondaryButton}>Demo datasheet <FileText size={17} /></DemoCTA></div><div className={styles.productFlags}><span><i /> Demo data only</span><span>No stock claim</span><span>No qualification claim</span></div></div></section><section className={styles.specificationLayout}><aside><a href="#specifications">Specifications</a><a href="#applications">Applications</a><a href="#documents">Documents</a></aside><div><section id="specifications" className={styles.specBlock}><header><span>ELECTRICAL / MECHANICAL DATA</span><b>Demo Rev A</b></header><table><tbody>{product.attributes.map((attribute) => <tr key={attribute.label}><th>{attribute.label}</th><td>{attribute.value}</td><td>Illustrative</td></tr>)}</tbody></table></section><section id="applications" className={styles.detailBlock}><span>DESIGN CONTEXT</span><h2>Illustrative applications</h2><div>{product.applications?.map((application) => <article key={application}><CircuitBoard /><b>{application}</b><p>Use the production site to connect verified application notes and selection limits.</p></article>)}</div></section><section id="documents" className={styles.documentBlock}><FileText /><div><span>CONTROLLED DOCUMENT / DEMO</span><h2>No technical file is downloaded.</h2><p>The production implementation would resolve the approved datasheet revision from ForgeBase document metadata.</p></div></section></div></section></ElectronicsShell>;
}

export function ElectronicsCategoryPage({ categorySlug }: { categorySlug: string }) {
  const category = data.categories.find((item) => item.slug === categorySlug)!;
  const products = data.products.filter((product) => product.categoryId === category.id);
  return <ElectronicsShell><PageHeader eyebrow="PRODUCT FAMILY" title={category.name} description={category.description ?? ""} /><section className={styles.familyFeature}><div className={styles.familyImage}><Image src={categoryImages[category.id]} alt={`Fictional ${category.name} technical product family`} fill loading="eager" sizes="(max-width: 800px) 100vw, 48vw" /></div><div><span>FAMILY FILTER</span><h2>{products.length} Demo configuration</h2><p>This page shows how a scalable category route can combine family guidance with the same normalized part records.</p><dl>{products[0].attributes.slice(0,3).map((attribute) => <div key={attribute.label}><dt>{attribute.label}</dt><dd>{attribute.value}</dd></div>)}</dl></div></section><ParametricCatalog products={products} categories={[category]} /></ElectronicsShell>;
}

export function ElectronicsApplicationsPage() {
  return <ElectronicsShell><PageHeader eyebrow="DESIGN CONTEXT / 02" title="Navigate from circuit requirement to shortlist." description="Application pages organize component families around interface, isolation, density and operating-condition questions." /><section className={styles.applicationPages}>{data.applications.map((application, index) => <article key={application.id}><header><span>APP / 0{index + 1}</span>{index === 0 ? <CircuitBoard /> : index === 1 ? <Zap /> : <PackageSearch />}</header><h2>{application.name}</h2><p>{application.description}</p><div><span>Relevant families</span>{data.categories.slice(index === 1 ? 1 : 0, index === 1 ? 3 : 2).map((category) => <Link key={category.id} href={`${electronicsBase}/categories/${category.slug}/`}>{category.name}<ArrowRight size={15} /></Link>)}</div></article>)}</section></ElectronicsShell>;
}

export function ElectronicsCertificationsPage() {
  return <ElectronicsShell><PageHeader eyebrow="QUALITY & COMPLIANCE / 03" title="Evidence status without invented assurance." description="A transparent record structure for material declarations, qualification evidence and controlled-document state." /><section className={styles.complianceTable}><header><span>RECORD</span><span>DEMO SCOPE</span><span>STATUS</span></header>{data.certifications.map((certification) => <article key={certification.id}><div><FileCheck2 /><b>{certification.name}</b></div><p>{certification.scope}</p><span>ILLUSTRATIVE</span></article>)}</section><section className={styles.labBanner}><div><Image src={images.lab} alt="Fictional component validation laboratory setup" fill sizes="(max-width: 800px) 100vw, 50vw" /></div><article><FlaskConical /><span>VALIDATION WORKFLOW</span><h2>Show method, revision and result ownership.</h2><p>The production site should publish only customer-approved evidence and make expired, superseded or pending records unmistakable.</p></article></section></ElectronicsShell>;
}

export function ElectronicsResourcesPage() {
  return <ElectronicsShell><PageHeader eyebrow="TECHNICAL LIBRARY / 04" title="Documents with product and revision context." description="A compact technical-library pattern for datasheets, application notes and design resources." /><section className={styles.resourceTable}>{electronicsResources.map((resource) => <article key={resource.code}><FileText /><div><span>{resource.code} / {resource.type}</span><h2>{resource.title}</h2><p>{resource.description}</p></div><b>{resource.revision}</b><DemoCTA cta={cta("electronics-datasheet")}>Demo record <ArrowRight size={15} /></DemoCTA></article>)}</section><div id="datasheet-demo-note" className={styles.documentNotice}><BookOpen /><div><h2>Document interface only.</h2><p>No file is downloaded. Each production record would require an approved file, owner, revision and effective date.</p></div></div></ElectronicsShell>;
}

export function ElectronicsAboutPage() {
  return <ElectronicsShell><PageHeader eyebrow="COMPANY / 05" title="A technical supplier story built on data stewardship." description="This fictional identity demonstrates how a component supplier can explain product-data ownership without claiming history, facilities or customers." /><section className={styles.aboutGrid}><article><span>01</span><Search /><h2>Selection clarity</h2><p>Normalize product attributes so engineers can search, filter and compare without translating inconsistent data.</p></article><article><span>02</span><FileCheck2 /><h2>Evidence control</h2><p>Connect specifications and compliance statements to approved, revision-aware source records.</p></article><article><span>03</span><Box /><h2>Sample context</h2><p>Carry the selected part and design stage into the commercial handoff without losing engineering intent.</p></article></section><div className={styles.companyDisclosure}><ShieldCheck /><div><h2>{data.site.companyName} is a demonstration identity.</h2><p>{data.site.legalNotice}. No manufacturing, distribution, inventory, compliance or qualification claim is made.</p></div></div></ElectronicsShell>;
}

export function ElectronicsRFQPage() {
  return <ElectronicsShell><div className={styles.samplePageIntro}><span>SAMPLE REQUEST / 06</span><h1>Carry the part context into the conversation.</h1></div><SampleRequest products={data.products} submitCTA={cta("electronics-submit")} /></ElectronicsShell>;
}
