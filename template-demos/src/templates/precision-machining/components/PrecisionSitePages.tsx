import Image from "next/image";
import { ArrowRight, Check, Crosshair, FileCheck2, Gauge, Layers3, ScanLine, ShieldCheck } from "lucide-react";
import { DemoRFQForm } from "@/components/DemoRFQForm";
import { DemoCTA } from "@/components/DemoCTA";
import type { TemplateProduct } from "@/contracts/forgebase";
import { precisionMachiningData as data } from "../data";
import { PrecisionSiteShell } from "./PrecisionSiteChrome";

const images = {
  hero: "/templates/precision-machining/hero-cnc-facility.png",
  machining: "/templates/precision-machining/capability-five-axis-machining.png",
  quality: "/templates/precision-machining/quality-cmm-inspection.png",
  parts: "/templates/precision-machining/parts-precision-components.png",
};

function InnerHero({ eyebrow, title, description, image, alt }: { eyebrow: string; title: string; description: string; image: string; alt: string }) {
  return (
    <section className="inner-hero">
      <div><p>{eyebrow}</p><h1>{title}</h1><span>{description}</span></div>
      <figure><Image src={image} alt={alt} fill loading="eager" sizes="(max-width: 900px) 100vw, 48vw" /><figcaption>FICTIONAL FACILITY / TEMPLATE PREVIEW</figcaption></figure>
    </section>
  );
}

function ProductCard({ product, index }: { product: TemplateProduct; index: number }) {
  return (
    <article className="full-product-card">
      <DemoCTA className={`full-product-image crop-${index + 1}`} cta={product.cta}>
        <Image src={images.parts} alt={`Fictional component collection representing ${product.name}`} fill loading="eager" sizes="(max-width: 760px) 100vw, 33vw" />
        <span>{product.modelNumber}</span>
      </DemoCTA>
      <div className="full-product-body">
        <p>{product.applications?.join(" / ")}</p>
        <h2><DemoCTA cta={product.cta}>{product.name}</DemoCTA></h2>
        <span>{product.shortDescription}</span>
        <dl>{product.attributes.map((attribute) => <div key={attribute.label}><dt>{attribute.label}</dt><dd>{attribute.value}</dd></div>)}</dl>
        <DemoCTA className="inline-arrow" cta={product.cta}>View part concept <ArrowRight size={17} /></DemoCTA>
      </div>
    </article>
  );
}

export function ProductsIndexPage() {
  return (
    <PrecisionSiteShell>
      <InnerHero eyebrow="PART FAMILIES / 01" title="Parts presented for engineering review." description="A product catalogue designed around material, tolerance, finish and application—not generic marketing cards." image={images.parts} alt="Collection of fictional machined aluminum, stainless steel and brass components" />
      <section className="inner-section product-index-section">
        <div className="section-mini-intro"><p>REPRESENTATIVE COMPONENTS</p><span>All components are fictional examples created for this template. A production site maps this structure to ForgeBase Products.</span></div>
        <div className="full-product-grid">{data.products.map((product, index) => <ProductCard product={product} index={index} key={product.id} />)}</div>
      </section>
      <ConversionBand />
    </PrecisionSiteShell>
  );
}

export function ProductDetailPage({ product }: { product: TemplateProduct }) {
  const cta = Object.fromEntries(data.ctas.map((item) => [item.id, item]));

  return (
    <PrecisionSiteShell>
      <section className="product-detail-hero">
        <div className="product-detail-image"><Image src={images.parts} alt={`Fictional machined component family including ${product.name}`} fill loading="eager" sizes="(max-width: 900px) 100vw, 55vw" /></div>
        <div className="product-detail-copy">
          <p>{product.modelNumber} / FICTIONAL PART CONCEPT</p>
          <h1>{product.name}</h1>
          <span>{product.shortDescription}</span>
          <dl>{product.attributes.map((attribute) => <div key={attribute.label}><dt>{attribute.label}</dt><dd>{attribute.value}</dd></div>)}</dl>
          <DemoCTA className="dark-action" cta={cta["product-detail-rfq"]}>Review a similar drawing <ArrowRight /></DemoCTA>
        </div>
      </section>
      <section className="inner-section detail-engineering-section">
        <div className="section-mini-intro"><p>ENGINEERING CONTEXT</p><span>This page demonstrates how a ForgeBase Product can support sourcing evaluation without claiming an off-the-shelf item exists.</span></div>
        <div className="engineering-columns">
          <article><ScanLine /><h2>Critical features</h2><p>Surface relationships, sealing areas and position-critical patterns can be explained alongside the structured specification.</p></article>
          <article><Layers3 /><h2>Material route</h2><p>Material grade, finish, certification requirement and lot traceability remain visible through the RFQ journey.</p></article>
          <article><Gauge /><h2>Volume context</h2><p>Prototype and recurring-production requirements can route to different qualification questions.</p></article>
        </div>
      </section>
      <ConversionBand title="Have a drawing with similar risks?" />
    </PrecisionSiteShell>
  );
}

export function CapabilitiesPage() {
  return (
    <PrecisionSiteShell>
      <InnerHero eyebrow="MANUFACTURING / 02" title="Capabilities buyers can actually evaluate." description="Connect process range, design constraints and inspection evidence to the type of work being sourced." image={images.machining} alt="Close view of a fictional five-axis milling setup cutting an aluminum component" />
      <section className="inner-section capability-detail-list">
        {data.capabilities.map((capability, index) => (
          <article key={capability.id}>
            <div className="capability-detail-number">0{index + 1}</div>
            <div><p>{index === 0 ? "COMPLEX GEOMETRY" : index === 1 ? "CONCENTRIC FEATURES" : "VERIFICATION"}</p><h2>{capability.name}</h2><span>{capability.description}</span></div>
            <dl>{capability.metrics?.map((metric) => <div key={metric.label}><dt>{metric.label}</dt><dd>{metric.value}</dd></div>)}</dl>
          </article>
        ))}
      </section>
      <section className="photo-evidence-band"><Image src={images.machining} alt="Fictional five-axis machining process" fill loading="eager" sizes="100vw" /><div><p>PROCESS IMAGE / DEMO</p><h2>Show the process. Explain the boundary.</h2><span>Formal capability statements must be replaced with customer-confirmed facts before a production launch.</span></div></section>
      <ConversionBand />
    </PrecisionSiteShell>
  );
}

export function ApplicationsPage() {
  const cta = Object.fromEntries(data.ctas.map((item) => [item.id, item]));

  return (
    <PrecisionSiteShell>
      <InnerHero eyebrow="APPLICATIONS / 03" title="Organize the site around sourcing context." description="Applications translate machining capabilities into the risks, evidence and decision criteria of different buying teams." image={images.hero} alt="Engineer observing a fictional five-axis CNC process" />
      <section className="inner-section industry-grid">
        {data.applications.map((application, index) => (
          <article key={application.id}><span>0{index + 1}</span><Crosshair /><h2>{application.name}</h2><p>{application.description}</p><ul><li>Relevant part families</li><li>Critical feature examples</li><li>Application-specific RFQ prompts</li></ul><DemoCTA cta={cta["application-rfq"]}>Discuss an application <ArrowRight size={17} /></DemoCTA></article>
        ))}
      </section>
      <ConversionBand title="Turn application context into a qualified RFQ." />
    </PrecisionSiteShell>
  );
}

export function QualityPage() {
  return (
    <PrecisionSiteShell>
      <InnerHero eyebrow="QUALITY SYSTEM / 04" title="Trust is built through visible controls." description="Present review, inspection, traceability and reporting as an operating system—not an unsupported badge wall." image={images.quality} alt="Quality engineer inspecting a fictional precision component on a coordinate measuring machine" />
      <section className="inner-section quality-process">
        <div className="section-mini-intro"><p>ILLUSTRATIVE CONTROL PLAN</p><span>The steps below are template content. They must be replaced by the customer’s verified quality workflow.</span></div>
        <ol>
          <li><span>01</span><div><h2>Drawing review</h2><p>Revision, CTQ features, materials and acceptance criteria are aligned before release.</p></div></li>
          <li><span>02</span><div><h2>Process planning</h2><p>Operations, fixtures and in-process controls are connected to identified risks.</p></div></li>
          <li><span>03</span><div><h2>Inspection</h2><p>Measurement methods and reporting requirements follow the agreed control plan.</p></div></li>
          <li><span>04</span><div><h2>Traceable release</h2><p>Material and lot evidence can accompany the shipment record where required.</p></div></li>
        </ol>
      </section>
      <section className="certification-demo-band"><ShieldCheck /><div><p>NO CERTIFICATION CLAIM</p><h2>Certification content remains structured—but explicitly unverified in this Demo.</h2></div><span>{data.certifications[0].scope}</span></section>
      <ConversionBand />
    </PrecisionSiteShell>
  );
}

export function AboutPage() {
  return (
    <PrecisionSiteShell>
      <InnerHero eyebrow="COMPANY TEMPLATE / 05" title="A credible company story without invented history." description="The Demo demonstrates hierarchy and evidence placement while clearly separating layout copy from facts a real customer must provide." image={images.hero} alt="Fictional unbranded precision machining facility" />
      <section className="inner-section about-principles">
        <div><p>THE TEMPLATE POSITION</p><h2>Engineering clarity over generic claims.</h2></div>
        <div className="principle-list">
          <article><span>01</span><h3>Show what can be verified</h3><p>Equipment, process, materials and controls should be attached to customer-approved evidence.</p></article>
          <article><span>02</span><h3>Explain how work is qualified</h3><p>Good B2B content helps buyers understand fit before consuming sales time.</p></article>
          <article><span>03</span><h3>Make the next step technical</h3><p>The primary conversion asks for the information required to evaluate manufacturability.</p></article>
        </div>
      </section>
      <section className="about-disclosure"><FileCheck2 /><div><h2>{data.site.companyName} is a demonstration identity.</h2><p>{data.site.legalNotice}. No factory history, customer relationship, equipment ownership or certification is claimed.</p></div></section>
      <ConversionBand />
    </PrecisionSiteShell>
  );
}

export function RFQPage() {
  const cta = Object.fromEntries(data.ctas.map((item) => [item.id, item]));

  return (
    <PrecisionSiteShell>
      <section className="standalone-rfq-page">
        <div className="rfq-page-intro"><p>DRAWING-LED RFQ / 06</p><h1>Give engineering enough context to respond.</h1><span>This static interaction demonstrates the future ForgeBase mapping. It never uploads, transmits or stores information.</span><ul><li><Check /> No data leaves this browser</li><li><Check /> No email is sent</li><li><Check /> No lead or contact is created</li></ul></div>
        <DemoRFQForm fields={data.rfqFields} submitCTA={cta["rfq-submit"]} />
      </section>
    </PrecisionSiteShell>
  );
}

function ConversionBand({ title = "Start with the drawing and the buying context." }: { title?: string }) {
  const cta = data.ctas.find((item) => item.id === "conversion-rfq")!;
  return <section className="conversion-band"><div><p>READY TO DISCUSS A PART?</p><h2>{title}</h2></div><DemoCTA cta={cta}>Open Demo RFQ <ArrowRight /></DemoCTA></section>;
}
