import LocalePage, {
  generateMetadata as localeGenerateMetadata,
} from "./[locale]/page";

export function generateMetadata() {
  return localeGenerateMetadata({ params: Promise.resolve({ locale: "en" }) });
}

export default function HomePage() {
  return LocalePage({ params: Promise.resolve({ locale: "en" }) });
}
