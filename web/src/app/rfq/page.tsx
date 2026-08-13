import LocalePage, {
  generateMetadata as localeGenerateMetadata,
} from "../[locale]/rfq/page";

type Props = {
  searchParams: Promise<{
    product_id?: string;
    product_ids?: string;
    application_id?: string;
    quantity?: string;
    specifications?: string;
    message?: string;
    requirement_summary?: string;
  }>;
};

export function generateMetadata({ searchParams }: Props) {
  return localeGenerateMetadata({ params: Promise.resolve({ locale: "en" }), searchParams });
}

export default function RFQPage({ searchParams }: Props) {
  return LocalePage({
    params: Promise.resolve({ locale: "en" }),
    searchParams,
  });
}
