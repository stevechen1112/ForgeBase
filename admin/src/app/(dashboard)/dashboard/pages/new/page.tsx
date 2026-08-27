import PageContentForm from "../PageContentForm";
export const metadata = { title: "新增頁面 — ForgeBase 管理後台" };

type Props = {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

export default async function NewPagePage({ searchParams }: Props) {
  const params = await searchParams;
  const prefill: Record<string, string> = {};
  if (typeof params.slug === "string") prefill.slug = params.slug;
  if (typeof params.locale === "string") prefill.locale = params.locale;
  const aiDraft = params.draft === "1";

  return (
    <div>
      <h1 className="mb-6 text-2xl font-semibold text-foreground">新增頁面</h1>
      <PageContentForm initial={Object.keys(prefill).length ? prefill : undefined} aiDraft={aiDraft} />
    </div>
  );
}
