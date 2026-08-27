import Image from "next/image";
import { ArrowRight, Check, Crosshair, FileCheck2, Gauge, ScanLine } from "lucide-react";
import { DemoRFQForm } from "@/components/DemoRFQForm";
import { DemoCTA } from "@/components/DemoCTA";
import { precisionMachiningData as data } from "../data";
import { PrecisionSiteShell } from "./PrecisionSiteChrome";

export function PrecisionMachiningTemplate() {
  const cta = Object.fromEntries(data.ctas.map((item) => [item.id, item]));

  return (
    <PrecisionSiteShell>
      <section className="machine-hero">
        <div className="hero-copy">
          <p className="machine-kicker">CNC MACHINING / CONTRACT MANUFACTURING</p>
          <h1>Tolerance is a number.<br /><span>Confidence is a system.</span></h1>
          <p>{data.site.tagline}</p>
          <div className="hero-actions">
            <DemoCTA cta={cta["hero-rfq"]}>Send your drawing <ArrowRight aria-hidden="true" /></DemoCTA>
            <DemoCTA cta={cta["hero-capabilities"]} />
          </div>
          <div className="hero-proof" aria-label="Illustrative capability highlights">
            <span><strong>±0.010</strong> mm demo tolerance</span>
            <span><strong>3–5 AXIS</strong> process concepts</span>
            <span><strong>FAIR</strong> inspection workflow</span>
          </div>
        </div>
        <div className="technical-visual">
          <Image
            src="/templates/precision-machining/hero-cnc-facility.png"
            alt="Engineer observing a fictional five-axis CNC machining process in an unbranded facility"
            fill
            loading="eager"
            sizes="(max-width: 900px) 100vw, 46vw"
          />
          <div className="technical-shade" />
          <div className="dimension dimension-x">120.00</div>
          <div className="dimension dimension-y">Ø48.00</div>
          <div className="visual-label"><ScanLine size={18} /> DEMO-M01 / REV.B</div>
        </div>
      </section>

      <section className="machine-marquee" aria-label="Key capabilities">
        <span>5-axis milling</span><i />
        <span>Precision turning</span><i />
        <span>Material traceability</span><i />
        <span>Inspection reporting</span>
      </section>

      <section className="machine-section capabilities-section" id="capabilities">
        <div className="section-heading">
          <p>01 / MANUFACTURING SYSTEM</p>
          <h2>Evidence before promises.</h2>
          <span>Structure the site around the questions sourcing teams ask before they release a drawing.</span>
        </div>
        <div className="capability-grid">
          {data.capabilities.map((capability, index) => (
            <article key={capability.id}>
              <span className="cap-index">0{index + 1}</span>
              {index === 0 ? <Crosshair /> : index === 1 ? <Gauge /> : <FileCheck2 />}
              <h3>{capability.name}</h3>
              <p>{capability.description}</p>
              {capability.metrics?.map((metric) => <dl key={metric.label}><dt>{metric.label}</dt><dd>{metric.value}</dd></dl>)}
            </article>
          ))}
        </div>
        <div className="capability-photo-grid">
          <figure>
            <Image src="/templates/precision-machining/capability-five-axis-machining.png" alt="Close view of a fictional five-axis milling setup cutting an aluminum component" fill sizes="(max-width: 900px) 100vw, 58vw" />
            <figcaption><span>PROCESS / DEMO</span> Five-axis machining concept</figcaption>
          </figure>
          <figure>
            <Image src="/templates/precision-machining/parts-precision-components.png" alt="Collection of fictional machined aluminum, stainless steel and brass components" fill sizes="(max-width: 900px) 100vw, 34vw" />
            <figcaption><span>PARTS / DEMO</span> Material and geometry range</figcaption>
          </figure>
        </div>
      </section>

      <section className="parts-section" id="parts">
        <div className="parts-intro">
          <p>02 / REPRESENTATIVE PARTS</p>
          <h2>Show the work at engineering resolution.</h2>
          <p>These are fictional component concepts. In a production site, the same presentation maps to ForgeBase Products and structured specifications.</p>
        </div>
        <div className="parts-list">
          {data.products.map((product, index) => (
            <article key={product.id}>
              <div className={`part-thumbnail part-visual-${index + 1}`} aria-hidden="true"><span /></div>
              <div className="part-name"><small>{product.modelNumber}</small><h3>{product.name}</h3><p>{product.shortDescription}</p></div>
              <dl className="part-specs">
                {product.attributes.map((attribute) => <div key={attribute.label}><dt>{attribute.label}</dt><dd>{attribute.value}</dd></div>)}
              </dl>
              <DemoCTA cta={product.cta}>{product.cta.label}<ArrowRight size={17} /></DemoCTA>
            </article>
          ))}
        </div>
        <figure className="parts-editorial-image">
          <Image src="/templates/precision-machining/parts-precision-components.png" alt="Collection of fictional machined aluminum, stainless steel and brass components" fill sizes="100vw" />
          <figcaption>Fictional component family · generated for this template preview</figcaption>
        </figure>
      </section>

      <section className="quality-section" id="quality">
        <div className="quality-copy">
          <p>03 / QUALITY NARRATIVE</p>
          <h2>Make risk reduction visible.</h2>
          <p>For technical buyers, quality is not a badge wall. The template turns inspection planning, traceability and reporting into a clear evaluation path.</p>
          <ul>
            <li><Check /> Drawing and revision review</li>
            <li><Check /> Process-linked inspection planning</li>
            <li><Check /> Material and lot traceability</li>
            <li><Check /> FAIR and measurement reports</li>
          </ul>
        </div>
        <div className="quality-panel quality-photo-panel">
          <Image src="/templates/precision-machining/quality-cmm-inspection.png" alt="Quality engineer inspecting a fictional precision component on a coordinate measuring machine" fill sizes="(max-width: 900px) 100vw, 52vw" />
          <div className="quality-photo-shade" />
          <div className="quality-panel-head"><span>ILLUSTRATIVE INSPECTION PLAN</span><strong>DEMO / NOT CERTIFIED</strong></div>
          <div className="quality-metrics"><span><b>CTQ</b> Critical features mapped</span><span><b>REV</b> Revision evidence retained</span><span><b>LOT</b> Material trail documented</span></div>
        </div>
      </section>

      <section className="rfq-section" id="rfq">
        <div className="rfq-intro">
          <p>04 / DRAWING-LED RFQ</p>
          <h2>Start with the part,<br />not a generic contact form.</h2>
          <p>The production version maps these fields to ForgeBase RFQ, custom specifications and secure attachments.</p>
          <div className="demo-company-note"><strong>{data.site.companyName}</strong><span>{data.site.legalNotice}</span><span>{data.site.location}</span></div>
        </div>
          <DemoRFQForm fields={data.rfqFields} submitCTA={cta["rfq-submit"]} />
      </section>

    </PrecisionSiteShell>
  );
}
