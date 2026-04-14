import type { Metadata } from "next";
import Script from "next/script";
import { NextIntlClientProvider } from "next-intl";
import { getLocale, getMessages } from "next-intl/server";
import "./globals.css";
import { buildDefaultMetadata } from "@/lib/seo";
import { getRuntimeSiteConfig } from "@/lib/runtimeSiteConfig";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { IndustrialHeader, IndustrialFooter } from "@/components/themes";

const GA_ID = process.env.NEXT_PUBLIC_GA_MEASUREMENT_ID;

export async function generateMetadata(): Promise<Metadata> {
  const runtimeSiteConfig = await getRuntimeSiteConfig();
  return buildDefaultMetadata(undefined, runtimeSiteConfig);
}

export default async function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const locale = await getLocale();
  const messages = await getMessages();
  const runtimeSiteConfig = await getRuntimeSiteConfig();
  const isIndustrial = runtimeSiteConfig.layout === "industrial";

  return (
    <html lang={locale} data-theme={runtimeSiteConfig.theme} data-layout={runtimeSiteConfig.layout}>
      <head>
        {/* Preconnect to CDN (Cloudflare R2) and Google services to reduce TTFB */}
        <link rel="preconnect" href={`https://${process.env.NEXT_PUBLIC_R2_HOSTNAME ?? "assets.example.com"}`} />
        <link rel="dns-prefetch" href={`https://${process.env.NEXT_PUBLIC_R2_HOSTNAME ?? "assets.example.com"}`} />
        {GA_ID && (
          <>
            <link rel="preconnect" href="https://www.googletagmanager.com" />
            <link rel="preconnect" href="https://www.google-analytics.com" />
          </>
        )}
      </head>
      <body className="flex min-h-screen flex-col">
        {/* GA4 — only injected when NEXT_PUBLIC_GA_MEASUREMENT_ID is set */}
        {GA_ID && (
          <>
            <Script
              src={`https://www.googletagmanager.com/gtag/js?id=${GA_ID}`}
              strategy="afterInteractive"
            />
            <Script id="ga4-init" strategy="afterInteractive">
              {`
                window.dataLayer = window.dataLayer || [];
                function gtag(){dataLayer.push(arguments);}
                gtag('js', new Date());
                gtag('config', '${GA_ID}', { send_page_view: false });
              `}
            </Script>
          </>
        )}

        <NextIntlClientProvider locale={locale} messages={messages}>
          {isIndustrial ? <IndustrialHeader siteConfig={runtimeSiteConfig} /> : <Header siteConfig={runtimeSiteConfig} />}
          <main className="flex-1">{children}</main>
          {isIndustrial ? <IndustrialFooter siteConfig={runtimeSiteConfig} /> : <Footer siteConfig={runtimeSiteConfig} />}
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
