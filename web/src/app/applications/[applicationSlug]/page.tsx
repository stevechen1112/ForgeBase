import LocalePage, {
  generateMetadata as localeGenerateMetadata,
} from "../../[locale]/applications/[applicationSlug]/page";

type Props = {
  params: Promise<{ applicationSlug: string }>;
};

export function generateMetadata({ params }: Props) {
  return localeGenerateMetadata({
    params: params.then((p) => ({ locale: "en", ...p })),
  });
}

export default function ApplicationDetailPage({ params }: Props) {
  return LocalePage({
    params: params.then((p) => ({ locale: "en", ...p })),
  });
}
