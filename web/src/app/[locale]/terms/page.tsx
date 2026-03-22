import type { Metadata } from "next";
import { Link } from "@/i18n/navigation";
import { getMessageNamespace } from "@/lib/messages";
import { resolveLocale } from "@/lib/siteCopy";

type CommonMessages = {
  home: string;
};

type LegalPageMessages = {
  metadata: Metadata;
  breadcrumb: string;
  title: string;
  paragraphs?: string[];
};

interface Props {
  params: Promise<{ locale: string }>;
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  await params;
  return getMessageNamespace<LegalPageMessages>("legal.terms").then((copy) => copy.metadata);
}

export default async function TermsPage({ params }: Props) {
  const { locale } = await params;
  resolveLocale(locale);
  const [common, copy] = await Promise.all([
    getMessageNamespace<CommonMessages>("common"),
    getMessageNamespace<LegalPageMessages>("legal.terms"),
  ]);
  return (
    <main>
      <section className="border-b border-gray-100 bg-gray-50 py-14">
        <div className="mx-auto max-w-4xl px-6">
          <nav aria-label="Breadcrumb" className="mb-3 text-xs text-gray-400">
            <Link href="/" className="hover:underline">{common.home}</Link>
            <span className="mx-1">/</span>
            <span className="text-gray-600">{copy.breadcrumb}</span>
          </nav>
          <h1 className="text-3xl font-bold text-gray-900">{copy.title}</h1>
        </div>
      </section>
      <section className="py-14">
        <div className="prose prose-gray mx-auto max-w-4xl px-6">
          {copy.paragraphs?.map((paragraph) => (
            <p key={paragraph}>{paragraph}</p>
          ))}
        </div>
      </section>
    </main>
  );
}
