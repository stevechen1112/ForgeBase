import type { Metadata } from "next";
import Script from "next/script";
import { NextIntlClientProvider } from "next-intl";
import { getLocale, getMessages } from "next-intl/server";
import "./globals.css";
import { buildDefaultMetadata } from "@/lib/seo";
import { siteConfig } from "@/lib/siteConfig";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { IndustrialHeader, IndustrialFooter } from "@/components/themes";

const isIndustrial = siteConfig.layout === "industrial";

const GA_ID = process.env.NEXT_PUBLIC_GA_MEASUREMENT_ID;

export const metadata: Metadata = buildDefaultMetadata();

export default async function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const locale = await getLocale();
  const messages = await getMessages();

  return (
    <html lang={locale} data-theme={siteConfig.theme}>
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
          {isIndustrial ? <IndustrialHeader /> : <Header />}
          <main className="flex-1">{children}</main>
          {isIndustrial ? <IndustrialFooter /> : <Footer />}
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
