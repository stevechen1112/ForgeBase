import LocalePage, {
  generateMetadata as localeGenerateMetadata,
} from "../../[locale]/faq/[tag]/page";

type Props = { params: Promise<{ tag: string }> };

export function generateMetadata({ params }: Props) {
  return localeGenerateMetadata({
    params: params.then((p) => ({ locale: "en", ...p })),
  });
}

export default function FAQTagPage({ params }: Props) {
  return LocalePage({
    params: params.then((p) => ({ locale: "en", ...p })),
  });
}
