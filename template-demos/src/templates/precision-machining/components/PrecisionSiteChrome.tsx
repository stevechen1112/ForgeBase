import Link from "next/link";
import { ArrowRight, Crosshair, Menu } from "lucide-react";
import { DemoNotice } from "@/components/DemoNotice";
import { DemoCTA } from "@/components/DemoCTA";
import { precisionMachiningData as data } from "../data";

export const precisionBase = "/templates/precision-machining";

const navigation = [
  { href: `${precisionBase}/products/`, label: "Parts" },
  { href: `${precisionBase}/capabilities/`, label: "Capabilities" },
  { href: `${precisionBase}/applications/`, label: "Industries" },
  { href: `${precisionBase}/quality/`, label: "Quality" },
  { href: `${precisionBase}/about/`, label: "About" },
];

function NavigationLinks() {
  const rfqCTA = data.ctas.find((item) => item.id === "nav-rfq")!;

  return (
    <>
      {navigation.map((item) => <Link href={item.href} key={item.href}>{item.label}</Link>)}
      <DemoCTA className="nav-rfq" cta={rfqCTA}>Send a drawing <ArrowRight size={16} /></DemoCTA>
    </>
  );
}

export function PrecisionHeader() {
  return (
    <>
      <DemoNotice />
      <header className="machine-header">
        <Link className="machine-logo" href={`${precisionBase}/`} aria-label="AxisForm Precision demo home">
          <Crosshair aria-hidden="true" />
          <span>AXISFORM<small>PRECISION / DEMO</small></span>
        </Link>
        <nav aria-label="Template navigation"><NavigationLinks /></nav>
        <details className="machine-mobile-nav">
          <summary aria-label="Open site navigation"><Menu /></summary>
          <nav aria-label="Mobile template navigation"><NavigationLinks /></nav>
        </details>
      </header>
    </>
  );
}

export function PrecisionFooter() {
  return (
    <footer className="machine-footer">
      <div className="machine-logo"><Crosshair /><span>AXISFORM<small>PRECISION / DEMO</small></span></div>
      <p>{data.site.disclosure.message}</p>
      <div className="footer-links">
        <Link href={`${precisionBase}/products/`}>Parts</Link>
        <Link href={`${precisionBase}/capabilities/`}>Capabilities</Link>
        <DemoCTA cta={data.ctas.find((item) => item.id === "nav-rfq")!}>RFQ</DemoCTA>
        <Link href="/">Template Lab</Link>
      </div>
    </footer>
  );
}

export function PrecisionSiteShell({ children }: { children: React.ReactNode }) {
  return <main className="machine-site"><PrecisionHeader />{children}<PrecisionFooter /></main>;
}
