import ApplicationForm from "../ApplicationForm";
export const metadata = { title: "新增應用場景 — NorthForge Admin" };

type Props = {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

export default async function NewApplicationPage({ searchParams }: Props) {
  const params = await searchParams;
  const prefill: Record<string, string> = {};
  if (typeof params.slug === "string") prefill.slug = params.slug;
  if (typeof params.locale === "string") prefill.locale = params.locale;

  return (
    <div>
      <h1 className="mb-6 text-2xl font-semibold text-foreground">新增應用場景</h1>
      <ApplicationForm initial={Object.keys(prefill).length ? prefill : undefined} />
    </div>
  );
}
