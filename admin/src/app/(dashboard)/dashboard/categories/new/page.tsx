import CategoryForm from "../CategoryForm";

export const metadata = { title: "新增分類 — NorthForge Admin" };

type Props = {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

export default async function NewCategoryPage({ searchParams }: Props) {
  const params = await searchParams;
  const prefill: Record<string, string> = {};
  if (typeof params.slug === "string") prefill.slug = params.slug;
  if (typeof params.locale === "string") prefill.locale = params.locale;
  const aiDraft = params.draft === "1";

  return (
    <div>
      <h1 className="mb-6 text-2xl font-semibold text-foreground">新增商品分類</h1>
      <CategoryForm initial={Object.keys(prefill).length ? prefill : undefined} aiDraft={aiDraft} />
    </div>
  );
}
