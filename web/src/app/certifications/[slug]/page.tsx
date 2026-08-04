import LocalePage, {
  generateMetadata as localeGenerateMetadata,
} from "../../[locale]/certifications/[slug]/page";

type Props = {
  params: Promise<{ slug: string }>;
};

export function generateMetadata({ params }: Props) {
  return localeGenerateMetadata({
    params: params.then((p) => ({ locale: "en", ...p })),
  });
}

export default function CertificationDetailPage({ params }: Props) {
  return LocalePage({
    params: params.then((p) => ({ locale: "en", ...p })),
  });
}
