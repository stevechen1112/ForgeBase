"use client";

import { FormEvent, useState } from "react";
import { CheckCircle2, PackageCheck } from "lucide-react";
import type { TemplateCTA, TemplateProduct } from "@/contracts/forgebase";
import styles from "./Electronics.module.css";

export function SampleRequest({ products, submitCTA }: { products: TemplateProduct[]; submitCTA: TemplateCTA }) {
  const [part, setPart] = useState(products[0].modelNumber ?? products[0].name);
  const [quantity, setQuantity] = useState("5 pieces");
  const [submitted, setSubmitted] = useState(false);
  const selected = products.find((product) => product.modelNumber === part) ?? products[0];

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitted(true);
  }

  if (submitted) return <section className={styles.sampleSuccess} role="status"><CheckCircle2 /><span>SAMPLE CART / DEMO COMPLETE</span><h1>Review request assembled.</h1><p>No sample, lead, contact, order or email was created. A production site would map this part context to ForgeBase.</p><button type="button" onClick={() => setSubmitted(false)}>Return to sample cart</button></section>;

  return <form className={styles.sampleWorkspace} onSubmit={submit}>
    <section className={styles.sampleCart}>
      <div className={styles.sampleCartHead}><PackageCheck /><div><span>SAMPLE CART</span><b>1 PART SELECTED</b></div></div>
      <div className={styles.samplePart}><span>{selected.modelNumber}</span><h2>{selected.name}</h2><p>{selected.shortDescription}</p><dl>{selected.attributes.slice(0,3).map((attribute) => <div key={attribute.label}><dt>{attribute.label}</dt><dd>{attribute.value}</dd></div>)}</dl></div>
      <div className={styles.sampleSafety}><CheckCircle2 /><p><b>Preview-safe interaction</b>No inventory is reserved and no information leaves this browser.</p></div>
    </section>
    <section className={styles.sampleFields}>
      <header><span>DESIGN CONTEXT</span><h1>Request a component review.</h1><p>Demonstrate a sample workflow without implying real stock, fulfilment or engineering approval.</p></header>
      <div className={styles.fieldGrid}>
        <label><span>Part number *</span><select value={part} onChange={(event) => setPart(event.target.value)} required>{products.map((product) => <option key={product.id}>{product.modelNumber}</option>)}</select></label>
        <label><span>Sample quantity *</span><select value={quantity} onChange={(event) => setQuantity(event.target.value)} required><option>5 pieces</option><option>10 pieces</option><option>25 pieces</option><option>Discuss quantity</option></select></label>
        <label><span>Design stage *</span><select required defaultValue=""><option value="" disabled>Choose stage</option><option>Architecture</option><option>Prototype</option><option>Validation</option><option>Pre-production</option></select></label>
        <label><span>Name *</span><input required placeholder="Your name" /></label>
        <label><span>Work email *</span><input type="email" required placeholder="name@company.com" /></label>
        <label><span>Company *</span><input required placeholder="Company name" /></label>
        <label className={styles.fullField}><span>Design requirements *</span><textarea required rows={5} placeholder="Interface, operating conditions, timing and qualification needs" /></label>
      </div>
      <p className={styles.formNote}>Submitting this preview does not transmit or save any information.</p>
      <button className={styles.sampleSubmit} type="submit" data-cta-id={submitCTA.id} data-cta-intent={submitCTA.intent}>{submitCTA.label}</button>
    </section>
  </form>;
}
