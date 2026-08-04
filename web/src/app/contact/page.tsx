import LocalePage, {
  generateMetadata as localeGenerateMetadata,
} from "../[locale]/contact/page";

export function generateMetadata() {
  return localeGenerateMetadata({ params: Promise.resolve({ locale: "en" }) });
}

export default function ContactPage() {
  return LocalePage({ params: Promise.resolve({ locale: "en" }) });
}
