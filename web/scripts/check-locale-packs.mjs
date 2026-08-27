import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const locales = ["en", "zh-TW", "ja", "fr", "ru"];
const source = JSON.parse(readFileSync(join(root, "messages", "en.json"), "utf8"));
const protectedTerms = [
  "ForgeBase", "NorthForge", "OEM", "ODM", "MOQ", "ISO",
  "RoHS", "REACH", "VDE", "CE", "IEC 60900", "WhatsApp", "LinkedIn",
  "EXW", "FCA", "FAS", "FOB", "CFR", "CIF", "CPT", "CIP", "DAP", "DPU", "DDP",
];
const corePaths = [
  "common.home",
  "common.demoNotice",
  "header.langSwitch",
  "header.nav.products",
  "forms.contact.submit",
  "forms.rfq.submit",
  "legal.privacy.title",
];

function kind(value) {
  if (Array.isArray(value)) return "array";
  if (value === null) return "null";
  return typeof value;
}

function walkShape(reference, candidate, path = "", locale = "en") {
  assert.equal(kind(candidate), kind(reference), `${path || "root"}: type mismatch`);
  if (Array.isArray(reference)) {
    assert.equal(candidate.length, reference.length, `${path}: array length mismatch`);
    reference.forEach((value, index) => walkShape(value, candidate[index], `${path}[${index}]`, locale));
    return;
  }
  if (reference && typeof reference === "object") {
    assert.deepEqual(Object.keys(candidate).sort(), Object.keys(reference).sort(), `${path}: keys mismatch`);
    for (const key of Object.keys(reference)) {
      walkShape(reference[key], candidate[key], path ? `${path}.${key}` : key, locale);
    }
    return;
  }
  if (typeof reference === "string") {
    assert.ok(candidate.length > 0 || reference.length === 0, `${path}: empty translation`);
    assert.ok(!/forgebase\.invalid|zztoken/i.test(candidate), `${path}: unresolved translation token`);
    if (path.endsWith(".value")) assert.equal(candidate, reference, `${path}: submitted value changed`);
    for (const term of ["fr", "ru", "ja"].includes(locale) ? protectedTerms : []) {
      const expected = reference.split(term).length - 1;
      if (expected) {
        const actual = candidate.split(term).length - 1;
        assert.equal(actual, expected, `${path}: protected term ${term} changed`);
      }
    }
    const sourceEmails = reference.match(/[\w.+-]+@[\w.-]+\.\w+/g) ?? [];
    for (const email of sourceEmails) assert.ok(candidate.includes(email), `${path}: email changed`);
  }
}

function nested(payload, path) {
  return path.split(".").reduce((value, key) => value[key], payload);
}

for (const locale of locales) {
  const payload = JSON.parse(readFileSync(join(root, "messages", `${locale}.json`), "utf8"));
  walkShape(source, payload, "", locale);
  if (locale !== "en") {
    for (const path of corePaths) {
      assert.notEqual(nested(payload, path), nested(source, path), `${locale}:${path} was not localized`);
    }
  }
  const allText = JSON.stringify(payload);
  if (locale === "ja") assert.match(allText, /[ぁ-んァ-ヶ一-龯]/, "ja: Japanese script missing");
  if (locale === "ru") assert.match(allText, /[А-Яа-яЁё]/, "ru: Cyrillic script missing");
}

console.log(`Locale packs passed: ${locales.length} complete message trees.`);
