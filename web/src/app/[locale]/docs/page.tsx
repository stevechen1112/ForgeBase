import type { Metadata } from "next";
import { Link } from "@/i18n/navigation";
import { getMessageNamespace } from "@/lib/messages";
import { resolveLocale } from "@/lib/siteCopy";

type CommonMessages = {
  home: string;
};

type DocsPageMessages = {
  metadata: Metadata;
  breadcrumb: string;
  title: string;
  description: string;
  docs: Array<{ title: string; desc: string }>;
  noteTitle: string;
  noteDescription: string;
};

interface Props {
  params: Promise<{ locale: string }>;
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  await params;
  return getMessageNamespace<DocsPageMessages>("docsPage").then((copy) => copy.metadata);
}

export default async function DocsPage({ params }: Props) {
  const { locale } = await params;
  resolveLocale(locale);
  const [common, copy] = await Promise.all([
    getMessageNamespace<CommonMessages>("common"),
    getMessageNamespace<DocsPageMessages>("docsPage"),
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
        <div className="mx-auto max-w-5xl px-6 grid gap-6 md:grid-cols-3">
          {copy.docs.map((doc) => (
            <div key={doc.title} className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
              <h2 className="text-lg font-semibold text-gray-900">{doc.title}</h2>
              <p className="mt-3 text-sm leading-relaxed text-gray-600">{doc.desc}</p>
            </div>
          ))}
        </div>
        <div className="mx-auto mt-8 max-w-5xl px-6">
          <div className="rounded-2xl border border-blue-100 bg-blue-50 p-6">
            <h2 className="text-lg font-semibold text-blue-900">{copy.noteTitle}</h2>
            <p className="mt-2 text-sm leading-relaxed text-blue-800">
              {copy.noteDescription}
            </p>
          </div>
        </div>
      </section>
    </main>
  );
}
