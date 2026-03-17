import { NextResponse } from "next/server";
import { createFaviconSvg, readDemoAsset } from "@/lib/demoAssetRoute";

export async function GET() {
  const existing = await readDemoAsset(["logo-northforge-mark.svg"]);

  return new NextResponse(existing?.buffer ?? createFaviconSvg(), {
    headers: {
      "Content-Type": "image/svg+xml; charset=utf-8",
      "Cache-Control": "public, max-age=86400",
    },
  });
}
