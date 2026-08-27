"use client";

import { FormEvent, useState } from "react";
import { ArrowLeft, ArrowRight, Check, CheckCircle2, FileUp } from "lucide-react";
import type { TemplateCTA } from "@/contracts/forgebase";
import styles from "./Machinery.module.css";

const systemOptions = [
  { value: "Forming system", code: "FS", label: "Forming", note: "Servo press and feed" },
  { value: "Processing cell", code: "PC", label: "Processing", note: "Flexible enclosed cell" },
  { value: "Handling automation", code: "HA", label: "Handling", note: "Robotic transfer" },
  { value: "Not sure yet", code: "?", label: "Undecided", note: "Start with the application" },
];

export function SystemConfigurator({ submitCTA }: { submitCTA: TemplateCTA }) {
  const [step, setStep] = useState(1);
  const [system, setSystem] = useState("");
  const [submitted, setSubmitted] = useState(false);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (step < 3) {
      setStep((current) => current + 1);
      return;
    }
    setSubmitted(true);
  }

  if (submitted) {
    return (
      <section className={styles.configuratorSuccess} role="status">
        <span className={styles.successIcon}><CheckCircle2 aria-hidden="true" /></span>
        <p>CONFIGURATION / COMPLETE</p>
        <h2>Demo system brief assembled.</h2>
        <span>No information was uploaded, transmitted, saved or emailed. A production site would map this configuration to ForgeBase RFQ and custom fields.</span>
        <button type="button" onClick={() => { setSubmitted(false); setStep(1); }}>Build another demo brief</button>
      </section>
    );
  }

  return (
    <form className={styles.configurator} onSubmit={handleSubmit}>
      <div className={styles.configHeader}>
        <div>
          <p>PROJECT CONFIGURATOR</p>
          <h1>Build the operating brief.</h1>
        </div>
        <ol aria-label="Configuration progress">
          {["System", "Operating data", "Contact"].map((label, index) => (
            <li key={label} className={step === index + 1 ? styles.activeStep : step > index + 1 ? styles.completeStep : undefined}>
              <span>{step > index + 1 ? <Check size={14} /> : `0${index + 1}`}</span>{label}
            </li>
          ))}
        </ol>
      </div>

      <div className={styles.configBody}>
        {step === 1 && (
          <fieldset className={styles.configStep}>
            <legend>Select an equipment direction</legend>
            <p>Choose the closest starting point. This only changes the on-screen Demo flow.</p>
            <div className={styles.systemOptions}>
              {systemOptions.map((option) => (
                <label key={option.value} className={system === option.value ? styles.selectedOption : undefined}>
                  <input type="radio" name="system" value={option.value} required checked={system === option.value} onChange={(event) => setSystem(event.target.value)} />
                  <strong>{option.code}</strong>
                  <span><b>{option.label}</b><small>{option.note}</small></span>
                  <i>{system === option.value ? <Check size={17} /> : <ArrowRight size={17} />}</i>
                </label>
              ))}
            </div>
          </fieldset>
        )}

        {step === 2 && (
          <fieldset className={styles.configStep}>
            <legend>Define the operating window</legend>
            <p>These fields model the inputs used to qualify a production-system concept.</p>
            <div className={styles.operatingGrid}>
              <label><span>Selected direction</span><input value={system} readOnly /></label>
              <label><span>Workpiece / material *</span><input name="material" required placeholder="Part family and material" /></label>
              <label><span>Target production rate *</span><input name="rate" required placeholder="Units per minute, hour or shift" /></label>
              <label><span>Current process</span><input name="process" placeholder="Manual, standalone or integrated" /></label>
              <label className={styles.fullField}><span>Constraints and success criteria *</span><textarea name="requirements" required rows={5} placeholder="Floor space, utilities, changeover, quality, timing…" /></label>
              <label className={`${styles.fileTile} ${styles.fullField}`}><FileUp aria-hidden="true" /><span><b>Attach line layout or requirement brief</b><small>Demo only — the file never leaves this browser</small></span><input name="attachment" type="file" /></label>
            </div>
          </fieldset>
        )}

        {step === 3 && (
          <fieldset className={styles.configStep}>
            <legend>Add the project contact</legend>
            <p>The production version would connect this context to a ForgeBase RFQ. This preview has no transmission or storage.</p>
            <div className={styles.operatingGrid}>
              <label><span>Name *</span><input name="name" required placeholder="Your name" /></label>
              <label><span>Work email *</span><input name="email" type="email" required placeholder="name@company.com" /></label>
              <label><span>Company *</span><input name="company" required placeholder="Company name" /></label>
              <label><span>Project timing</span><input name="timing" placeholder="Target quarter or date" /></label>
              <div className={`${styles.safetyPanel} ${styles.fullField}`}><CheckCircle2 /><div><b>Safe Demo interaction</b><span>No lead, contact, opportunity, upload or email will be created.</span></div></div>
            </div>
          </fieldset>
        )}
      </div>

      <div className={styles.configFooter}>
        <span>STEP {step} OF 3 / {system || "NO SYSTEM SELECTED"}</span>
        <div>
          {step > 1 && <button className={styles.backButton} type="button" onClick={() => setStep((current) => current - 1)}><ArrowLeft size={17} /> Back</button>}
          <button className={styles.nextButton} type="submit" data-cta-id={submitCTA.id} data-cta-intent={submitCTA.intent}>
            {step === 3 ? submitCTA.label : "Continue"}<ArrowRight size={17} />
          </button>
        </div>
      </div>
    </form>
  );
}
