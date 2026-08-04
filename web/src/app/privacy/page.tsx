import LocalePage, {
  generateMetadata as localeGenerateMetadata,
} from "../[locale]/privacy/page";

export function generateMetadata() {
  return localeGenerateMetadata({ params: Promise.resolve({ locale: "en" }) });
}

export default function Page() {
  return LocalePage({ params: Promise.resolve({ locale: "en" }) });
}
