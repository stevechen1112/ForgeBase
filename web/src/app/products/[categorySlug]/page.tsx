import LocalePage, {
  generateMetadata as localeGenerateMetadata,
} from "../../[locale]/products/[categorySlug]/page";

type Props = {
  params: Promise<{ categorySlug: string }>;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

export function generateMetadata({ params, searchParams }: Props) {
  return localeGenerateMetadata({
    params: params.then((p) => ({ locale: "en", ...p })),
    searchParams: searchParams ?? Promise.resolve({}),
  });
}

export default function CategoryPage({ params, searchParams }: Props) {
  return LocalePage({
    params: params.then((p) => ({ locale: "en", ...p })),
    searchParams,
  });
}
