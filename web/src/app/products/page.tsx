/**
 * English (prefixless) routes delegate to the [locale] implementations so
 * industrial layout / i18n messages stay in sync when theme=industrial.
 */
import LocalePage, {
  generateMetadata as localeGenerateMetadata,
} from "../[locale]/products/page";

export function generateMetadata() {
  return localeGenerateMetadata({ params: Promise.resolve({ locale: "en" }) });
}

export default function ProductsPage() {
  return LocalePage({ params: Promise.resolve({ locale: "en" }) });
}
