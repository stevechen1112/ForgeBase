import type { Metadata } from "next";
import { Link } from "@/i18n/navigation";
import { getMessageNamespace } from "@/lib/messages.server";
import { resolveLocale } from "@/lib/siteCopy";
import { getRuntimeSiteContext } from "@/lib/runtimeSiteConfig";
import { IndustrialPageHero } from "@/components/themes";

type CommonMessages = {
  home: string;
};

type DealersPageMessages = {
  metadata: Metadata;
  breadcrumb: string;
  title: string;
  intro?: string;
  regionTitle?: string;
  regions?: string[];
  asideTitle?: string;
  asideDescription?: string;
};

interface Props {
  params: Promise<{ locale: string }>;
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  await params;
  return getMessageNamespace<DealersPageMessages>("legal.dealers").then((copy) => copy.metadata);
}

export default async function DealersPage({ params }: Props) {
  const { isIndustrial } = await getRuntimeSiteContext();
  const { locale } = await params;
  resolveLocale(locale);
  const [copy, common] = await Promise.all([
    getMessageNamespace<DealersPageMessages>("legal.dealers"),
    getMessageNamespace<CommonMessages>("common"),
  ]);

  if (isIndustrial) {
    return (
      <main className="bg-white">
        <IndustrialPageHero
          items={[
            { label: common.home, href: "/" },
            { label: copy.breadcrumb },
          ]}
          eyebrow="Channels"
          title={copy.title}
          description={copy.intro}
        />
        <section className="py-16">
          <div className="mx-auto grid max-w-6xl gap-8 px-6 lg:grid-cols-[1fr,0.9fr]">
            <div className="border border-gray-300 bg-white p-6">
              <h2 className="text-xl font-black uppercase tracking-wide text-gray-900">{copy.regionTitle}</h2>
              <ul className="mt-5 space-y-3 text-sm text-gray-600">
                {copy.regions?.map((region) => (
                  <li key={region} className="border-l-4 border-gray-200 bg-gray-50 px-4 py-3">{region}</li>
                ))}
              </ul>
            </div>
            <div className="border-l-4 border-primary bg-gray-50 p-6">
              <h2 className="text-lg font-black uppercase tracking-wide text-gray-900">{copy.asideTitle}</h2>
              <p className="mt-3 text-sm leading-relaxed text-gray-600">{copy.asideDescription}</p>
            </div>
          </div>
        </section>
      </main>
    );
  }

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
          <p className="mt-3 max-w-2xl text-gray-600">{copy.intro}</p>
        </div>
      </section>
      <section className="py-14">
        <div className="mx-auto max-w-5xl px-6 grid gap-8 lg:grid-cols-[1fr,0.9fr]">
          <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
            <h2 className="text-xl font-semibold text-gray-900">{copy.regionTitle}</h2>
            <ul className="mt-4 space-y-3 text-sm text-gray-600">
              {copy.regions?.map((region) => (
                <li key={region} className="rounded-lg bg-gray-50 px-4 py-3">{region}</li>
              ))}
            </ul>
          </div>
          <div className="rounded-xl border border-blue-100 bg-blue-50 p-6">
            <h2 className="text-lg font-semibold text-blue-900">{copy.asideTitle}</h2>
            <p className="mt-3 text-sm leading-relaxed text-blue-800">{copy.asideDescription}</p>
          </div>
        </div>
      </section>
    </main>
  );
}
