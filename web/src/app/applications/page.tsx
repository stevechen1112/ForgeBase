import LocalePage, {
  generateMetadata as localeGenerateMetadata,
} from "../[locale]/applications/page";

export function generateMetadata() {
  return localeGenerateMetadata({ params: Promise.resolve({ locale: "en" }) });
}

export default function ApplicationsPage() {
  return LocalePage({ params: Promise.resolve({ locale: "en" }) });
}
