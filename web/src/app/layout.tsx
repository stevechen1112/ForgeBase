import type { Metadata } from "next";
import { NextIntlClientProvider } from "next-intl";
import { getLocale, getMessages } from "next-intl/server";
import "./globals.css";
import { buildDefaultMetadata } from "@/lib/seo";
import { getRuntimeSiteConfig } from "@/lib/runtimeSiteConfig";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { IndustrialHeader, IndustrialFooter, PrecisionHeader, PrecisionFooter } from "@/components/themes";
import { DemoEnvironmentNotice } from "@/components/layout/DemoEnvironmentNotice";
import { AnalyticsConsent } from "@/components/tracking/AnalyticsConsent";
import { LayoutChatWidget } from "@/components/chat/LayoutChatWidget";
import { mergeMessageTrees, resolveSiteCopyOverlay } from "@/lib/messages";

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
  const baseMessages = await getMessages();
  const runtimeSiteConfig = await getRuntimeSiteConfig();
  const isIndustrial = runtimeSiteConfig.layout === "industrial";
  const isPrecision = runtimeSiteConfig.layout === "precision";
  const messages = mergeMessageTrees(baseMessages, resolveSiteCopyOverlay(runtimeSiteConfig.siteCopy, locale));

  return (
    <html lang={locale} data-theme={runtimeSiteConfig.theme} data-layout={runtimeSiteConfig.layout}>
      <head>
        {/* Preconnect to CDN (Cloudflare R2) and Google services to reduce TTFB */}
        <link rel="preconnect" href={`https://${process.env.NEXT_PUBLIC_R2_HOSTNAME ?? "assets.example.com"}`} />
        <link rel="dns-prefetch" href={`https://${process.env.NEXT_PUBLIC_R2_HOSTNAME ?? "assets.example.com"}`} />
      </head>
      <body className="flex min-h-screen flex-col">
        {/* GA4 — only injected when NEXT_PUBLIC_GA_MEASUREMENT_ID is set */}
        <NextIntlClientProvider locale={locale} messages={messages}>
          {isPrecision ? <PrecisionHeader siteConfig={runtimeSiteConfig} /> : isIndustrial ? <IndustrialHeader siteConfig={runtimeSiteConfig} /> : <Header siteConfig={runtimeSiteConfig} />}
          <DemoEnvironmentNotice />
          <main className="flex-1">{children}</main>
          {isPrecision ? <PrecisionFooter siteConfig={runtimeSiteConfig} /> : isIndustrial ? <IndustrialFooter siteConfig={runtimeSiteConfig} /> : <Footer siteConfig={runtimeSiteConfig} />}
          <LayoutChatWidget />
          <AnalyticsConsent measurementId={GA_ID} />
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
