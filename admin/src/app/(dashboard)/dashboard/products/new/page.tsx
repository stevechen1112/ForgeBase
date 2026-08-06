import ProductForm from "../ProductForm";

export const metadata = { title: "新增商品 — NorthForge Admin" };

type Props = {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

export default async function NewProductPage({ searchParams }: Props) {
  const params = await searchParams;
  const prefill: Record<string, string> = {};
  if (typeof params.slug === "string") prefill.slug = params.slug;
  if (typeof params.locale === "string") prefill.locale = params.locale;
  const aiDraft = params.draft === "1";

  return (
    <div>
      <h1 className="mb-6 text-2xl font-semibold text-foreground">新增商品</h1>
      <ProductForm initial={Object.keys(prefill).length ? prefill : undefined} aiDraft={aiDraft} />
    </div>
  );
}
