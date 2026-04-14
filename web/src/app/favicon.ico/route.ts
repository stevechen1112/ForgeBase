import { NextResponse } from "next/server";
import { getRuntimeSiteConfig } from "@/lib/runtimeSiteConfig";
import { createFaviconSvg, readDemoAsset } from "@/lib/demoAssetRoute";

export async function GET() {
  const runtimeSiteConfig = await getRuntimeSiteConfig();
  const existing = await readDemoAsset(["logo-mark.svg", "logo-brand-mark.svg"], runtimeSiteConfig.demoCompanyFolder);

  return new NextResponse(existing?.buffer ?? createFaviconSvg(runtimeSiteConfig), {
    headers: {
      "Content-Type": "image/svg+xml; charset=utf-8",
      "Cache-Control": "public, max-age=86400",
    },
  });
}
