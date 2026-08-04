import LocalePage, {
  generateMetadata as localeGenerateMetadata,
} from "../../../[locale]/products/[categorySlug]/[productSlug]/page";

type Props = {
  params: Promise<{ categorySlug: string; productSlug: string }>;
};

export function generateMetadata({ params }: Props) {
  return localeGenerateMetadata({
    params: params.then((p) => ({ locale: "en", ...p })),
  });
}

export default function ProductDetailPage({ params }: Props) {
  return LocalePage({
    params: params.then((p) => ({ locale: "en", ...p })),
  });
}
