import Image from "next/image";
import Link from "next/link";
import { ArrowRight, Boxes, Check, Factory, FileText, Gauge, Menu, Settings, ShieldCheck, SlidersHorizontal, Wrench, Workflow } from "lucide-react";
import { DemoCTA } from "@/components/DemoCTA";
import { DemoNotice } from "@/components/DemoNotice";
import type { TemplateProduct } from "@/contracts/forgebase";
import { industrialBase, industrialMachineryData as data, industrialResources, industrialServices } from "../data";
import styles from "./Machinery.module.css";
import { SystemConfigurator } from "./SystemConfigurator";

const images = {
  hero: `${industrialBase}/hero-servo-forming-line.png`,
  family: `${industrialBase}/equipment-family.png`,
  process: `${industrialBase}/coil-forming-process.png`,
  service: `${industrialBase}/field-service-maintenance.png`,
};

function cta(id: string) {
  return data.ctas.find((item) => item.id === id)!;
}

const navigation = [
  { code: "01", label: "Systems", href: `${industrialBase}/products/` },
  { code: "02", label: "Applications", href: `${industrialBase}/applications/` },
  { code: "03", label: "Engineering", href: `${industrialBase}/capabilities/` },
  { code: "04", label: "Service", href: `${industrialBase}/services/` },
  { code: "05", label: "Resources", href: `${industrialBase}/resources/` },
  { code: "06", label: "Company", href: `${industrialBase}/about/` },
];

function Brand() {
  return <Link href={`${industrialBase}/`} className={styles.brand} aria-label="Vantera Systems demo home"><span className={styles.brandMark}><Settings aria-hidden="true" /></span><span>VANTERA<small>PRODUCTION SYSTEMS</small></span></Link>;
}

function NavigationLinks() {
  return <>{navigation.map((item) => <Link key={item.href} href={item.href}><span>{item.code}</span>{item.label}</Link>)}</>;
}

export function MachineryShell({ children }: { children: React.ReactNode }) {
  return (
    <main className={styles.site}>
      <DemoNotice message="本頁為工業設備示意範本；不代表真實設備、產能或服務據點，也不傳送詢價。" />
      <div className={styles.frame}>
        <aside className={styles.sideRail}>
          <Brand />
          <nav aria-label="Industrial machinery navigation"><NavigationLinks /></nav>
          <div className={styles.railStatus}><span>DEMO ENVIRONMENT</span><b><i /> Interface online</b><small>No live equipment data</small></div>
          <DemoCTA cta={cta("machinery-nav-rfq")} className={styles.railCta}>Configure a system <ArrowRight size={17} /></DemoCTA>
        </aside>
        <div className={styles.canvas}>
          <header className={styles.mobileHeader}>
            <Brand />
            <details className={styles.mobileNav}><summary aria-label="Open machinery site navigation"><Menu /></summary><nav aria-label="Mobile industrial machinery navigation"><NavigationLinks /><DemoCTA cta={cta("machinery-nav-rfq")}>Configure a system</DemoCTA></nav></details>
          </header>
          <div className={styles.pageContent}>{children}</div>
          <footer className={styles.footer}><div><Brand /><p>{data.site.disclosure.message}</p></div><div><Link href={`${industrialBase}/products/`}>System index</Link><DemoCTA cta={cta("machinery-nav-rfq")}>Configurator</DemoCTA><Link href="/">Template Lab</Link></div></footer>
        </div>
      </div>
    </main>
  );
}

function PageTopline({ path, children }: { path: string; children?: React.ReactNode }) {
  return <div className={styles.topline}><span>VANTERA / {path}</span><div><b><i /> DEMO DATA</b>{children}</div></div>;
}

function ProductSelector({ compact = false }: { compact?: boolean }) {
  return <div className={compact ? styles.productRows : styles.selectorBar}>{data.products.map((product, index) => (
    <DemoCTA key={product.id} cta={product.cta} className={styles.selectorItem}>
      <span>0{index + 1}</span><div><b>{product.name}</b><small>{data.categories.find((category) => category.id === product.categoryId)?.name}</small></div><ArrowRight size={18} />
    </DemoCTA>
  ))}</div>;
}

function DashboardMetric({ label, value, note }: { label: string; value: string; note: string }) {
  return <div className={styles.dashboardMetric}><span>{label}</span><strong>{value}</strong><small>{note}</small></div>;
}

function ConversionPanel({ title = "Turn operating conditions into a system brief." }: { title?: string }) {
  return <section className={styles.conversionPanel}><div><span>PROJECT INPUT READY</span><h2>{title}</h2></div><DemoCTA cta={cta("machinery-hero-rfq")} className={styles.consoleButton}>Open configurator <ArrowRight /></DemoCTA></section>;
}

export function IndustrialMachineryTemplate() {
  return <MachineryShell>
    <PageTopline path="SYSTEM SELECTOR"><span>REV 2.0</span></PageTopline>
    <section className={styles.selectorHero}>
      <div className={styles.selectorIntro}>
        <p>PRODUCTION-SYSTEM WORKSPACE</p>
        <h1>Find the system boundary before the machine.</h1>
        <span>{data.site.tagline}</span>
        <div className={styles.introActions}><DemoCTA cta={cta("machinery-hero-rfq")} className={styles.consoleButton}>Start configuration <ArrowRight /></DemoCTA><DemoCTA cta={cta("machinery-compare")} className={styles.outlineButton}>Open system index</DemoCTA></div>
      </div>
      <div className={styles.systemViewer}>
        <div className={styles.viewerToolbar}><span>ACTIVE CONCEPT</span><b>FORMA / S420</b><i>ILLUSTRATIVE</i></div>
        <div className={styles.viewerImage}><Image src={images.hero} alt="Fictional unbranded automated servo forming line in a modern factory" fill loading="eager" sizes="(max-width: 900px) 100vw, 58vw" /></div>
        <div className={styles.viewerReadout}><DashboardMetric label="SYSTEM TYPE" value="FORMING" note="Servo platform" /><DashboardMetric label="TARGET MODE" value="80 SPM" note="Demo maximum" /><DashboardMetric label="PROJECT GATE" value="FAT / SAT" note="Acceptance concept" /></div>
      </div>
    </section>
    <ProductSelector />
    <section className={styles.dashboardSection}>
      <div className={styles.sectionTitle}><span>01 / QUALIFICATION LOGIC</span><h2>A buying interface organized like an engineering review.</h2></div>
      <div className={styles.dashboardGrid}>
        <article className={styles.flowModule}><div className={styles.moduleHead}><span>INPUT → OUTPUT MAP</span><b>APPLICATION STUDY</b></div><div className={styles.flowDiagram}><div><small>01</small><Factory /><b>Workpiece</b><span>Geometry / material</span></div><i /><div><small>02</small><SlidersHorizontal /><b>Operating window</b><span>Rate / changeover</span></div><i /><div><small>03</small><Workflow /><b>System boundary</b><span>Interfaces / scope</span></div><i /><div><small>04</small><ShieldCheck /><b>Acceptance</b><span>Evidence / handover</span></div></div></article>
        <article className={styles.signalModule}><span>PROJECT SIGNALS</span><DashboardMetric label="CONCEPT FAMILIES" value="03" note="Fictional equipment" /><DashboardMetric label="VERIFIED CLAIMS" value="00" note="Demo disclosure" /><DashboardMetric label="FORM MODE" value="LOCAL" note="No transmission" /></article>
        <article className={styles.imageModule}><Image src={images.process} alt="Fictional coil-fed forming process with guarded equipment and safe operator position" fill sizes="(max-width: 900px) 100vw, 55vw" /><span>MATERIAL FLOW / DEMO CELL</span></article>
        <article className={styles.checklistModule}><span>WHAT THE BUYER CAN RESOLVE</span><ul><li><Check />Which equipment family fits</li><li><Check />Where integration ownership changes</li><li><Check />What acceptance evidence is needed</li><li><Check />Which lifecycle services belong in scope</li></ul><DemoCTA cta={cta("machinery-applications")}>Open application map <ArrowRight size={17} /></DemoCTA></article>
      </div>
    </section>
    <section className={styles.serviceConsole}><div className={styles.serviceVisual}><Image src={images.service} alt="Fictional field service technician performing preventive maintenance on industrial equipment" fill sizes="(max-width: 900px) 100vw, 45vw" /><span>SERVICE MODULE / DEMONSTRATION</span></div><div className={styles.serviceConsoleCopy}><span>04 / LIFECYCLE LAYER</span><h2>Keep service inside the configuration.</h2><p>Installation, training, preventive maintenance and spare-parts planning appear as system requirements—not an afterthought below the catalogue.</p><div className={styles.serviceCodes}>{industrialServices.map((service) => <div key={service.number}><b>{service.number}</b><span>{service.name}</span></div>)}</div><DemoCTA cta={cta("machinery-service")}>Inspect service model <ArrowRight size={17} /></DemoCTA></div></section>
    <ConversionPanel />
  </MachineryShell>;
}

function ConsoleHeader({ code, title, description }: { code: string; title: string; description: string }) {
  return <><PageTopline path={code} /><header className={styles.consoleHeader}><span>{code}</span><div><h1>{title}</h1><p>{description}</p></div></header></>;
}

function MachineRow({ product, index }: { product: TemplateProduct; index: number }) {
  return <article className={styles.machineRow}>
    <div className={styles.rowIndex}>0{index + 1}</div>
    <div className={styles.rowImage}><Image src={images.family} alt={`Fictional unbranded equipment family representing ${product.name}`} fill loading="eager" sizes="(max-width: 900px) 100vw, 24vw" /></div>
    <div className={styles.rowSummary}><span>{product.modelNumber}</span><h2>{product.name}</h2><p>{product.shortDescription}</p><DemoCTA cta={product.cta}>Open system record <ArrowRight size={17} /></DemoCTA></div>
    <dl className={styles.rowSpecs}>{product.attributes.map((attribute) => <div key={attribute.label}><dt>{attribute.label}</dt><dd>{attribute.value}</dd></div>)}</dl>
  </article>;
}

export function MachineryProductsPage() {
  return <MachineryShell><ConsoleHeader code="SYSTEM INDEX / 01" title="Compare operating envelopes." description="A catalogue presented as an equipment-selection workspace: system family, operating range and integration question in one view." /><section className={styles.catalogControls}><span><SlidersHorizontal size={16} /> FILTER VIEW</span><button>All systems / 03</button><button>Forming / 01</button><button>Processing / 01</button><button>Handling / 01</button></section><section className={styles.machineRows}>{data.products.map((product, index) => <MachineRow key={product.id} product={product} index={index} />)}</section><section className={styles.matrixSection}><div className={styles.moduleHead}><span>SYSTEM COMPARISON</span><b>DEMO SELECTION MATRIX</b></div><div className={styles.matrixScroll}><table className={styles.comparison}><thead><tr><th>Concept</th><th>Primary use</th><th>Operating range</th><th>Integration question</th></tr></thead><tbody>{data.products.map((product) => <tr key={product.id}><td>{product.name}</td><td>{product.applications?.join(" / ")}</td><td>{product.attributes[0].value}</td><td>{product.categoryId === "cat-forming" ? "Feed and tooling" : product.categoryId === "cat-processing" ? "Extraction and nesting" : "Upstream / downstream handoff"}</td></tr>)}</tbody></table></div></section><ConversionPanel /></MachineryShell>;
}

export function MachineryProductDetailPage({ product }: { product: TemplateProduct }) {
  return <MachineryShell><PageTopline path={`SYSTEM RECORD / ${product.modelNumber}`} /><section className={styles.recordHeader}><div className={styles.recordTitle}><span>FICTIONAL EQUIPMENT CONCEPT</span><h1>{product.name}</h1><p>{product.shortDescription}</p><DemoCTA cta={cta("machinery-hero-rfq")} className={styles.consoleButton}>Configure similar system <ArrowRight /></DemoCTA></div><div className={styles.recordVisual}><Image src={images.family} alt={`Fictional industrial equipment family including ${product.name}`} fill loading="eager" sizes="(max-width: 900px) 100vw, 50vw" /><span>{product.modelNumber} / NOT A COMMERCIAL OFFER</span></div></section><section className={styles.recordData}><div><span>OPERATING DATA</span><dl>{product.attributes.map((attribute) => <div key={attribute.label}><dt>{attribute.label}</dt><dd>{attribute.value}</dd></div>)}</dl></div><div className={styles.boundaryMap}><span>PROJECT BOUNDARY</span><div><article><Gauge /><b>Production target</b><p>Cycle, availability and changeover assumptions.</p></article><ArrowRight /><article><Workflow /><b>Integration</b><p>Material, controls and ownership interfaces.</p></article><ArrowRight /><article><ShieldCheck /><b>Acceptance</b><p>Buyer-defined output and evidence plan.</p></article></div></div></section><ConversionPanel title={`Test ${product.name} against the operating brief.`} /></MachineryShell>;
}

export function MachineryApplicationsPage() {
  return <MachineryShell><ConsoleHeader code="APPLICATION MAP / 02" title="Begin with the production condition." description="Navigate by workpiece context and qualification question before choosing a machine family." /><section className={styles.applicationMap}>{data.applications.map((application, index) => <article key={application.id}><header><span>A-0{index + 1}</span><Factory /></header><h2>{application.name}</h2><p>{application.description}</p><dl><div><dt>INPUT</dt><dd>Workpiece and material</dd></div><div><dt>DECISION</dt><dd>Rate and changeover</dd></div><div><dt>OUTPUT</dt><dd>Qualified concept</dd></div></dl><DemoCTA cta={cta("machinery-hero-rfq")}>Configure this application <ArrowRight size={17} /></DemoCTA></article>)}</section><ConversionPanel /></MachineryShell>;
}

export function MachineryCapabilitiesPage() {
  return <MachineryShell><ConsoleHeader code="ENGINEERING PATH / 03" title="Make project gates visible." description="Feasibility, integration and acceptance are shown as a connected decision path instead of generic capability cards." /><section className={styles.engineeringPath}>{data.capabilities.map((capability, index) => <article key={capability.id}><span>GATE 0{index + 1}</span><div><b>{index === 0 ? "QUALIFY" : index === 1 ? "DEFINE" : "ACCEPT"}</b><h2>{capability.name}</h2><p>{capability.description}</p></div><strong>{capability.metrics?.[0].value}</strong></article>)}</section><section className={styles.engineeringEvidence}><div><ShieldCheck /><span>DEMO LIMIT</span><h2>No conformity or certification is claimed.</h2></div><ul>{data.certifications.map((certification) => <li key={certification.id}><b>{certification.name}</b><span>{certification.scope}</span></li>)}</ul></section><ConversionPanel /></MachineryShell>;
}

export function MachineryServicesPage() {
  return <MachineryShell><ConsoleHeader code="SERVICE NETWORK / 04" title="Plan the system after start-up." description="A lifecycle workspace for installation, training, maintenance and escalation expectations." /><section className={styles.serviceWorkspace}><div className={styles.serviceVisual}><Image src={images.service} alt="Fictional service technician inspecting an industrial equipment control cabinet" fill loading="eager" sizes="(max-width: 900px) 100vw, 48vw" /><span>FIELD SERVICE / ILLUSTRATIVE</span></div><div className={styles.serviceQueue}>{industrialServices.map((service) => <article key={service.number}><span>{service.number}</span><Wrench /><div><h2>{service.name}</h2><p>{service.description}</p></div><b>PLAN</b></article>)}</div></section><ConversionPanel title="Add lifecycle requirements to the system scope." /></MachineryShell>;
}

export function MachineryResourcesPage() {
  return <MachineryShell><ConsoleHeader code="DOCUMENT CONTROL / 05" title="Technical resources with revision context." description="A controlled-document interface for qualification tools, acceptance plans and utility worksheets." /><section className={styles.documentList}>{industrialResources.map((resource, index) => <article key={resource.code}><span>0{index + 1}</span><FileText /><div><small>{resource.code} / {resource.format}</small><h2>{resource.title}</h2><p>{resource.description}</p></div><DemoCTA cta={cta("machinery-resource")}>Preview status <ArrowRight size={17} /></DemoCTA></article>)}</section><div id="resource-demo-note" className={styles.demoPanel}><FileText /><div><h2>Interface demonstrations only.</h2><p>No file is downloaded. A production ForgeBase site would connect each record to a controlled, customer-approved document and revision.</p></div></div><ConversionPanel /></MachineryShell>;
}

export function MachineryAboutPage() {
  return <MachineryShell><ConsoleHeader code="OPERATING PRINCIPLES / 06" title="Project accountability, shown as a system." description="A fictional company narrative organized around decision ownership rather than invented history, scale or customer claims." /><section className={styles.principles}><article><span>01</span><Boxes /><h2>Application before catalogue</h2><p>Begin with production conditions before recommending an equipment family.</p></article><article><span>02</span><Workflow /><h2>One project boundary</h2><p>Clarify tooling, material flow, controls, utilities and acceptance ownership.</p></article><article><span>03</span><Wrench /><h2>Lifecycle in scope</h2><p>Make training, maintenance and support expectations part of the commercial conversation.</p></article></section><div className={styles.demoPanel}><ShieldCheck /><div><h2>{data.site.companyName} is a demonstration identity.</h2><p>{data.site.legalNotice}. No equipment ownership, installed base, customer relationship, conformity status or service location is claimed.</p></div></div><ConversionPanel /></MachineryShell>;
}

export function MachineryRFQPage() {
  return <MachineryShell><PageTopline path="PROJECT CONFIGURATOR / 07" /><SystemConfigurator submitCTA={cta("machinery-submit")} /></MachineryShell>;
}
