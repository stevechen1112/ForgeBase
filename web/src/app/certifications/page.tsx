import LocalePage, {
  generateMetadata as localeGenerateMetadata,
} from "../[locale]/certifications/page";

export function generateMetadata() {
  return localeGenerateMetadata({ params: Promise.resolve({ locale: "en" }) });
}

export default function CertificationsPage() {
  return LocalePage({ params: Promise.resolve({ locale: "en" }) });
}
