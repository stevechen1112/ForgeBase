import FAQForm from "../FAQForm";
export const metadata = { title: "新增常見問題 — ForgeBase 管理後台" };

type Props = {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

export default async function NewFAQPage({ searchParams }: Props) {
  const params = await searchParams;
  const prefill: Record<string, string> = {};
  if (typeof params.locale === "string") prefill.locale = params.locale;
  if (typeof params.category_tag === "string") prefill.category_tag = params.category_tag;
  if (typeof params.draft_group === "string") prefill.draft_group = params.draft_group;
  if (typeof params.variant_key === "string") prefill.variant_key = params.variant_key;
  const aiDraft = params.draft === "1";

  return (
    <div>
      <h1 className="mb-6 text-2xl font-semibold text-foreground">新增常見問題</h1>
      <FAQForm initial={Object.keys(prefill).length ? prefill : undefined} aiDraft={aiDraft} />
    </div>
  );
}
