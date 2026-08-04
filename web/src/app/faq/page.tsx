import LocalePage, {
  generateMetadata as localeGenerateMetadata,
} from "../[locale]/faq/page";

export function generateMetadata() {
  return localeGenerateMetadata({ params: Promise.resolve({ locale: "en" }) });
}

export default function FAQPage() {
  return LocalePage({ params: Promise.resolve({ locale: "en" }) });
}
