"use client";

import { FormEvent, useState } from "react";
import { CheckCircle2, Upload } from "lucide-react";
import type { TemplateCTA, TemplateRFQField } from "@/contracts/forgebase";

export function DemoRFQForm({
  fields,
  submitCTA,
  filePrompt = "Upload drawing (demo only)",
  successContext = "A production site would map this interaction to ForgeBase RFQ.",
}: {
  fields: TemplateRFQField[];
  submitCTA: TemplateCTA;
  filePrompt?: string;
  successContext?: string;
}) {
  const [submitted, setSubmitted] = useState(false);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitted(true);
  }

  if (submitted) {
    return (
      <div className="rfq-success" role="status">
        <CheckCircle2 aria-hidden="true" size={34} />
        <div>
          <h3>Demo interaction complete</h3>
          <p>No information was uploaded, transmitted, saved or emailed. {successContext}</p>
          <button type="button" onClick={() => setSubmitted(false)}>Return to the demo form</button>
        </div>
      </div>
    );
  }

  return (
    <form className="rfq-form" onSubmit={handleSubmit}>
      {fields.map((field) => (
        <label key={field.id} className={field.type === "textarea" || field.type === "file" ? "wide" : undefined}>
          <span>{field.label}{field.required ? " *" : ""}</span>
          {field.type === "select" ? (
            <select name={field.id} required={field.required} defaultValue="">
              <option value="" disabled>Choose an option</option>
              {field.options?.map((option) => <option key={option}>{option}</option>)}
            </select>
          ) : field.type === "textarea" ? (
            <textarea name={field.id} required={field.required} placeholder={field.placeholder} rows={4} />
          ) : field.type === "file" ? (
            <span className="file-field">
              <Upload aria-hidden="true" size={18} /> {filePrompt}
              <input name={field.id} type="file" />
            </span>
          ) : (
            <input name={field.id} type={field.type} required={field.required} placeholder={field.placeholder} />
          )}
        </label>
      ))}
      <p className="form-disclosure wide">Submitting this preview does not transmit or save any information.</p>
      <button className="rfq-submit wide" type="submit" data-cta-id={submitCTA.id} data-cta-intent={submitCTA.intent}>{submitCTA.label}</button>
    </form>
  );
}
