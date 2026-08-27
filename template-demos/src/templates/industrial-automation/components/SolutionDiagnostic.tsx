"use client";

import { FormEvent, useMemo, useState } from "react";
import { ArrowRight, CheckCircle2, CircleDot, Layers3 } from "lucide-react";
import type { TemplateCTA } from "@/contracts/forgebase";
import styles from "./Automation.module.css";

const constraints = ["Labor coverage", "Quality escapes", "Cycle-time variation", "Mixed-model complexity"] as const;
const boundaries = ["Standalone cell", "Existing machine / PLC", "Line controls", "MES / production data"] as const;

export function SolutionDiagnostic({ submitCTA }: { submitCTA: TemplateCTA }) {
  const [constraint, setConstraint] = useState<(typeof constraints)[number]>(constraints[0]);
  const [boundary, setBoundary] = useState<(typeof boundaries)[number]>(boundaries[1]);
  const [submitted, setSubmitted] = useState(false);
  const direction = useMemo(() => {
    if (constraint === "Quality escapes") return "Start with decision criteria, imaging conditions and reject confirmation.";
    if (constraint === "Mixed-model complexity") return "Start with recipe ownership, variant states and exception recovery.";
    if (constraint === "Cycle-time variation") return "Start with state timing, waiting conditions and recovery paths.";
    return "Start with operator travel, machine dwell and material presentation.";
  }, [constraint]);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitted(true);
  }

  if (submitted) return <section className={styles.diagnosticSuccess} aria-live="polite"><CheckCircle2 /><span>DEMO BRIEF PREPARED</span><h2>Your diagnostic context stayed in this browser.</h2><p>No meeting, lead, contact record or email was created. A production ForgeBase site would send approved fields into its governed lead workflow.</p><button type="button" onClick={() => setSubmitted(false)}>Revise the brief</button></section>;

  return <form className={styles.diagnostic} onSubmit={submit}>
    <section className={styles.diagnosticChoices}><header><CircleDot /><div><span>SIGNAL 01</span><h2>What is constraining the line?</h2></div></header><div>{constraints.map((item) => <button key={item} type="button" aria-pressed={constraint === item} onClick={() => setConstraint(item)}>{item}</button>)}</div></section>
    <section className={styles.diagnosticChoices}><header><Layers3 /><div><span>BOUNDARY 02</span><h2>Where must the system connect?</h2></div></header><div>{boundaries.map((item) => <button key={item} type="button" aria-pressed={boundary === item} onClick={() => setBoundary(item)}>{item}</button>)}</div></section>
    <aside className={styles.diagnosticBrief}><span>LIVE DIAGNOSTIC BRIEF</span><dl><div><dt>Constraint</dt><dd>{constraint}</dd></div><div><dt>Boundary</dt><dd>{boundary}</dd></div><div><dt>Discovery direction</dt><dd>{direction}</dd></div></dl><label>Name<input name="name" required placeholder="Your name" /></label><label>Work email<input name="email" type="email" required placeholder="name@company.com" /></label><label>Current process<textarea name="process" required placeholder="Describe the present workflow and desired outcome" /></label><button type="submit" data-cta-id={submitCTA.id} data-cta-intent={submitCTA.intent}>{submitCTA.label}<ArrowRight /></button><small>Static Demo: submission is intercepted locally.</small></aside>
  </form>;
}
