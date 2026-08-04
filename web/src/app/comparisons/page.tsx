import LocalePage, {
  generateMetadata as localeGenerateMetadata,
} from "../[locale]/comparisons/page";

export function generateMetadata() {
  return localeGenerateMetadata({ params: Promise.resolve({ locale: "en" }) });
}

export default function ComparisonsPage() {
  return LocalePage({ params: Promise.resolve({ locale: "en" }) });
}
