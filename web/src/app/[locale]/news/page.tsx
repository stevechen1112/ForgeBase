import type { Metadata } from "next";
import { Link } from "@/i18n/navigation";
import { getMessageNamespace } from "@/lib/messages";
import { resolveLocale } from "@/lib/siteCopy";

type CommonMessages = {
  home: string;
};

type NewsPageMessages = {
  metadata: Metadata;
  breadcrumb: string;
  title: string;
  description: string;
  items: Array<{ date: string; title: string; summary: string }>;
};

interface Props {
  params: Promise<{ locale: string }>;
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  await params;
  return getMessageNamespace<NewsPageMessages>("newsPage").then((copy) => copy.metadata);
}

export default async function NewsPage({ params }: Props) {
  const { locale } = await params;
  resolveLocale(locale);
  const [common, copy] = await Promise.all([
    getMessageNamespace<CommonMessages>("common"),
    getMessageNamespace<NewsPageMessages>("newsPage"),
  ]);
  return (
    <main>
      <section className="border-b border-gray-100 bg-gray-50 py-14">
        <div className="mx-auto max-w-5xl px-6">
          <nav aria-label="Breadcrumb" className="mb-3 text-xs text-gray-400">
            <Link href="/" className="hover:underline">{common.home}</Link>
            <span className="mx-1">/</span>
            <span className="text-gray-600">{copy.breadcrumb}</span>
          </nav>
          <h1 className="text-3xl font-bold text-gray-900">{copy.title}</h1>
          <p className="mt-3 max-w-2xl text-gray-600">{copy.description}</p>
        </div>
      </section>
      <section className="py-14">
        <div className="mx-auto max-w-5xl px-6 space-y-6">
          {copy.items.map((item) => (
            <article key={item.title} className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
              <p className="text-xs font-semibold uppercase tracking-widest text-blue-600">{item.date}</p>
              <h2 className="mt-2 text-xl font-semibold text-gray-900">{item.title}</h2>
              <p className="mt-3 text-sm leading-relaxed text-gray-600">{item.summary}</p>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}
