import Image from "next/image";
import Link from "next/link";
import { ArrowDown, ArrowRight, Blocks, Bot, Braces, Cable, Check, ChevronRight, Gauge, Menu, Network, ScanLine, ShieldCheck, TimerReset, Workflow } from "lucide-react";
import { DemoCTA } from "@/components/DemoCTA";
import { DemoNotice } from "@/components/DemoNotice";
import type { TemplateProduct } from "@/contracts/forgebase";
import { automationBase, automationCases, industrialAutomationData as data, integrationLayers } from "../data";
import { AutomationMap } from "./AutomationMap";
import { SolutionDiagnostic } from "./SolutionDiagnostic";
import styles from "./Automation.module.css";

const images = {
  line: `${automationBase}/connected-robotic-line.png`,
  tending: `${automationBase}/robotic-machine-tending.png`,
  vision: `${automationBase}/machine-vision-inspection.png`,
  commissioning: `${automationBase}/automation-commissioning.png`,
};

const solutionImages: Record<string, string> = {
  "robotic-machine-tending": images.tending,
  "machine-vision-inspection": images.vision,
  "flexible-assembly-cell": images.line,
};

const navigation = [
  { label: "Solutions", href: `${automationBase}/solutions/` },
  { label: "Applications", href: `${automationBase}/applications/` },
  { label: "Integration", href: `${automationBase}/capabilities/` },
  { label: "Outcomes", href: `${automationBase}/case-studies/` },
  { label: "Company", href: `${automationBase}/about/` },
];

function cta(id: string) { return data.ctas.find((item) => item.id === id)!; }

function Brand() {
  return <Link href={`${automationBase}/`} className={styles.brand} aria-label="Kinetra Automation demo home"><span><i /><i /><i /></span><b>KINETRA<small>AUTOMATION / DEMO</small></b></Link>;
}

export function AutomationShell({ children }: { children: React.ReactNode }) {
  return <main className={styles.site}>
    <DemoNotice message="Fictional automation provider. Systems, results, credentials and contact details are illustrative; no inquiry is transmitted." />
    <header className={styles.header}><Brand /><nav>{navigation.map((item) => <Link key={item.href} href={item.href}>{item.label}</Link>)}</nav><DemoCTA cta={cta("automation-nav-contact")} className={styles.headerCta}>Book consultation <ArrowRight /></DemoCTA><details className={styles.mobileNav}><summary aria-label="Open automation site navigation"><Menu /></summary><div>{navigation.map((item) => <Link key={item.href} href={item.href}>{item.label}</Link>)}<DemoCTA cta={cta("automation-nav-contact")}>Book consultation</DemoCTA></div></details></header>
    {children}
    <footer className={styles.footer}><div><Brand /><p>{data.site.disclosure.message}</p></div><div><span>SYSTEM MAP</span>{navigation.slice(0,4).map((item) => <Link key={item.href} href={item.href}>{item.label}</Link>)}</div><div><span>DEMO BOUNDARY</span><p>{data.site.legalNotice}. No system, installation, customer or performance claim is made.</p><Link href="/">Return to Template Lab</Link></div></footer>
  </main>;
}

function PageIntro({ code, title, description }: { code: string; title: string; description: string }) {
  return <header className={styles.pageIntro}><span>{code}</span><h1>{title}</h1><p>{description}</p><ArrowDown /></header>;
}

function SolutionCard({ solution, index }: { solution: TemplateProduct; index: number }) {
  return <article className={styles.solutionCard}><div className={styles.solutionPhoto}><Image src={solutionImages[solution.slug]} alt={`Fictional automation solution representing ${solution.name}`} fill sizes="(max-width: 800px) 100vw, 34vw" /></div><div className={styles.solutionMeta}><span>0{index + 1} / {solution.modelNumber}</span><h2>{solution.name}</h2><p>{solution.shortDescription}</p><dl>{solution.attributes.slice(0,2).map((attribute) => <div key={attribute.label}><dt>{attribute.label}</dt><dd>{attribute.value}</dd></div>)}</dl><DemoCTA cta={solution.cta}>Trace the architecture <ArrowRight /></DemoCTA></div></article>;
}

export function IndustrialAutomationTemplate() {
  return <AutomationShell>
    <section className={styles.hero}><div className={styles.heroCopy}><span>ROBOTICS · VISION · CONTROLS · DATA</span><h1>Connect the line.<br/><em>Clarify the outcome.</em></h1><p>Map the physical process, control states and production-data boundary before committing to equipment.</p><div><DemoCTA cta={cta("automation-diagnostic")} className={styles.primaryButton}>Diagnose your line <ArrowRight /></DemoCTA><DemoCTA cta={cta("automation-solutions")} className={styles.ghostButton}>Explore system concepts</DemoCTA></div></div><div className={styles.heroMap}><AutomationMap /></div><div className={styles.heroPhoto}><Image src={images.line} alt="Fictional connected robotic production line with infeed, guarded robot, machine and outfeed" fill priority sizes="100vw" /><span>CONNECTED CELL / ILLUSTRATIVE</span><div><b>5</b><small>system states mapped</small></div></div></section>
    <section className={styles.signalStrip}><span>START WITH THE CONSTRAINT</span>{data.applications.map((item, index) => <article key={item.id}><b>0{index + 1}</b><p>{item.name}</p></article>)}</section>
    <section className={styles.homeSolutions}><header><span>SOLUTION SYSTEMS / 01</span><h2>Architecture before equipment.</h2><p>Each system concept exposes the process, control and data decisions that have to align.</p></header><div>{data.products.map((solution, index) => <SolutionCard key={solution.id} solution={solution} index={index} />)}</div></section>
    <section className={styles.layerStage}><div className={styles.layerIntro}><span>INTEGRATION STACK / 02</span><h2>One outcome.<br/>Four connected layers.</h2><p>An automation proposal becomes credible when responsibility is explicit from the physical process through production context.</p><DemoCTA cta={{...cta("automation-solutions"), id:"automation-capabilities-home", href:`${automationBase}/capabilities/`}}>See integration capability <ArrowRight /></DemoCTA></div><div className={styles.layerStack}>{integrationLayers.map((layer) => <article key={layer.code}><b>{layer.code}</b><div><h3>{layer.name}</h3><p>{layer.detail}</p></div></article>)}</div></section>
    <section className={styles.outcomeFeature}><div className={styles.outcomePhoto}><Image src={images.commissioning} alt="Fictional automation engineer commissioning a guarded robotic cell" fill sizes="(max-width: 800px) 100vw, 54vw" /></div><div className={styles.outcomeCopy}><span>ACCEPTANCE PATH / 03</span><h2>Make handoff part of the design.</h2><p>Discovery, controls review, FAT, site acceptance and lifecycle support appear as one visible sequence—not hidden after the proposal.</p><ol><li><b>01</b>Constraint & acceptance criteria</li><li><b>02</b>Interface & safety review</li><li><b>03</b>FAT → SAT → controlled change</li></ol><DemoCTA cta={cta("automation-case-studies")}>Review Demo outcomes <ArrowRight /></DemoCTA></div></section>
  </AutomationShell>;
}

export function AutomationSolutionsPage() {
  return <AutomationShell><PageIntro code="SOLUTIONS / 01" title="System concepts organized around production decisions." description="Three fictional solution families demonstrate how ForgeBase can connect a buyer's constraint to architecture, interfaces and consultation context." /><section className={styles.solutionIndex}>{data.products.map((solution, index) => <SolutionCard key={solution.id} solution={solution} index={index} />)}</section><section className={styles.mapSection}><header><span>COMMON SYSTEM LANGUAGE</span><h2>Trace the state, not just the hardware.</h2></header><AutomationMap /></section></AutomationShell>;
}

export function AutomationSolutionPage({ solution }: { solution: TemplateProduct }) {
  const category = data.categories.find((item) => item.id === solution.categoryId)!;
  return <AutomationShell><div className={styles.breadcrumbs}><Link href={`${automationBase}/solutions/`}>Solutions</Link><ChevronRight /><span>{category.name}</span><ChevronRight /><b>{solution.name}</b></div><section className={styles.solutionHero}><div className={styles.solutionHeroCopy}><span>{solution.modelNumber} / DEMO</span><h1>{solution.name}</h1><p>{solution.shortDescription}</p><DemoCTA cta={cta("automation-diagnostic")} className={styles.primaryButton}>Discuss this boundary <ArrowRight /></DemoCTA></div><div><Image src={solutionImages[solution.slug]} alt={`Fictional ${solution.name} automation system`} fill priority sizes="(max-width: 800px) 100vw, 52vw" /><span>ILLUSTRATIVE SYSTEM</span></div></section><section className={styles.architectureGrid}><aside><span>SYSTEM QUESTION</span><h2>What has to be true at every handoff?</h2><p>These illustrative attributes are discussion boundaries, not guaranteed product specifications.</p></aside><div>{solution.attributes.map((attribute, index) => <article key={attribute.label}><b>0{index + 1}</b><span>{attribute.label}</span><h3>{attribute.value}</h3></article>)}</div></section><section className={styles.applicationBand}><span>APPLICATION CONTEXT</span>{solution.applications?.map((application) => <article key={application}><Check /><b>{application}</b><p>Confirm part, process, exception and acceptance context during discovery.</p></article>)}</section><section className={styles.mapSection}><AutomationMap /></section></AutomationShell>;
}

export function AutomationApplicationsPage() {
  const icons = [Bot, ScanLine, Workflow];
  return <AutomationShell><PageIntro code="APPLICATIONS / 02" title="Begin with the operating constraint." description="Application framing keeps the buyer's production problem ahead of robot model, camera count or software label." /><section className={styles.applicationMatrix}>{data.applications.map((application, index) => { const Icon = icons[index]; return <article key={application.id}><header><span>0{index + 1}</span><Icon /></header><h2>{application.name}</h2><p>{application.description}</p><dl><div><dt>Observe</dt><dd>{index === 0 ? "Travel, dwell, replenishment" : index === 1 ? "Defect, image, disposition" : "Variant, recipe, exception"}</dd></div><div><dt>Connect</dt><dd>{index === 0 ? "Robot ↔ machine" : index === 1 ? "Camera ↔ PLC ↔ reject" : "Station ↔ line ↔ MES"}</dd></div></dl></article>; })}</section><section className={styles.diagnosticCallout}><div><span>APPLICATION DIAGNOSTIC</span><h2>Turn the symptom into a reviewable system brief.</h2></div><DemoCTA cta={cta("automation-diagnostic")}>Open diagnostic <ArrowRight /></DemoCTA></section></AutomationShell>;
}

export function AutomationCapabilitiesPage() {
  return <AutomationShell><PageIntro code="INTEGRATION / 03" title="Responsibility across every system layer." description="A credible integrator page makes discovery, controls, validation and lifecycle boundaries easy to inspect." /><section className={styles.capabilityFlow}>{data.capabilities.map((capability, index) => <article key={capability.id}><header><b>0{index + 1}</b><span>{index === 0 ? "FRAME" : index === 1 ? "CONNECT" : "HAND OFF"}</span></header><h2>{capability.name}</h2><p>{capability.description}</p><strong>{capability.metrics?.[0].value}</strong></article>)}</section><section className={styles.layerStage}><div className={styles.layerIntro}><span>CONTROL ARCHITECTURE</span><h2>Expose the interface boundary.</h2><p>Each layer is a different ownership conversation. The production implementation would map approved technical records to these claims.</p></div><div className={styles.layerStack}>{integrationLayers.map((layer) => <article key={layer.code}><b>{layer.code}</b><div><h3>{layer.name}</h3><p>{layer.detail}</p></div></article>)}</div></section><section className={styles.commissioningGrid}><div><Image src={images.commissioning} alt="Fictional engineer performing safe robotic-cell commissioning" fill sizes="(max-width: 800px) 100vw, 50vw" /></div><article><Cable /><span>COMMISSIONING EVIDENCE</span><h2>Acceptance is a managed sequence.</h2><ul><li><Check />Illustrative interface review record</li><li><Check />Illustrative FAT / SAT structure</li><li><Check />Illustrative training and change log</li></ul><p>No actual engineering, safety assessment or certification is represented.</p></article></section></AutomationShell>;
}

export function AutomationCaseStudiesPage() {
  return <AutomationShell><PageIntro code="OUTCOMES / 04" title="Before and after, with the boundary still visible." description="These fictional scenarios demonstrate outcome storytelling without inventing a customer, installation or verified result." /><section className={styles.caseTimeline}>{automationCases.map((item) => <article key={item.code}><header><span>{item.code}</span><b>{item.sector}</b></header><h2>{item.title}</h2><div><section><small>BEFORE</small><p>{item.before}</p></section><ArrowRight/><section><small>AFTER / CONCEPT</small><p>{item.after}</p></section></div><footer><strong>{item.outcome}</strong><span>{item.boundary}</span></footer></article>)}</section><section className={styles.diagnosticCallout}><div><span>YOUR LINE / NOT A CLAIM</span><h2>Build a brief from your own constraint.</h2></div><DemoCTA cta={cta("automation-diagnostic")}>Start diagnostic <ArrowRight /></DemoCTA></section></AutomationShell>;
}

export function AutomationAboutPage() {
  return <AutomationShell><PageIntro code="COMPANY / 05" title="An integrator narrative built around accountable boundaries." description="Kinetra Automation is a fictional identity used to demonstrate the complete ForgeBase content model and buyer journey." /><section className={styles.principles}>{[{icon:Gauge,title:"Outcome before equipment",body:"Frame the operating constraint and acceptance test first."},{icon:Network,title:"Interfaces made visible",body:"Name the technical and organizational owner of every handoff."},{icon:TimerReset,title:"Lifecycle in scope",body:"Treat commissioning, recovery and change control as design inputs."}].map((item,index)=>{const Icon=item.icon;return <article key={item.title}><span>0{index+1}</span><Icon/><h2>{item.title}</h2><p>{item.body}</p></article>;})}</section><section className={styles.disclosurePanel}><ShieldCheck/><div><span>DEMONSTRATION IDENTITY</span><h2>No real company, facility or customer is represented.</h2><p>{data.site.legalNotice}. Every system image, credential record, result and contact detail exists solely for a safe, realistic website preview.</p></div></section><section className={styles.recordGrid}>{data.certifications.map((record)=><article key={record.id}><Braces/><h3>{record.name}</h3><p>{record.scope}</p><b>DEMO ONLY</b></article>)}</section></AutomationShell>;
}

export function AutomationContactPage() {
  return <AutomationShell><PageIntro code="DIAGNOSTIC / 06" title="Map the constraint before the consultation." description="Select the operating symptom and system boundary to preview the context a production ForgeBase workflow could carry into a qualified conversation." /><SolutionDiagnostic submitCTA={cta("automation-submit")} /><section className={styles.contactBoundary}><Blocks/><div><h2>This preview sends nothing.</h2><p>No meeting is booked and no lead, contact, CRM record or email is created. The interaction exists to test form comprehension, CTA attribution and local success handling.</p></div></section></AutomationShell>;
}
