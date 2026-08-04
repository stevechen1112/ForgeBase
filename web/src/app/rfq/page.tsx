import LocalePage, {
  generateMetadata as localeGenerateMetadata,
} from "../[locale]/rfq/page";

type Props = {
  searchParams: Promise<{ product_id?: string; application_id?: string }>;
};

export function generateMetadata() {
  return localeGenerateMetadata({ params: Promise.resolve({ locale: "en" }) });
}

export default function RFQPage({ searchParams }: Props) {
  return LocalePage({
    params: Promise.resolve({ locale: "en" }),
    searchParams,
  });
}
