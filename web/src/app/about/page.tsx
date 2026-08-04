import LocalePage, {
  generateMetadata as localeGenerateMetadata,
} from "../[locale]/about/page";

export function generateMetadata() {
  return localeGenerateMetadata({ params: Promise.resolve({ locale: "en" }) });
}

export default function AboutPage() {
  return LocalePage({ params: Promise.resolve({ locale: "en" }) });
}
