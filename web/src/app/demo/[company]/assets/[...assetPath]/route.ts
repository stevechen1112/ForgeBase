import { NextResponse } from "next/server";
import { createDemoAssetResponse } from "@/lib/demoAssetRoute";
import { getRuntimeSiteConfig } from "@/lib/runtimeSiteConfig";

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ company: string; assetPath: string[] }> },
) {
  const { company, assetPath } = await params;
  const siteConfig = await getRuntimeSiteConfig();

  // Asset URLs are tenant-scoped too: a host cannot enumerate another
  // connected tenant's mounted demo folder by changing one path segment.
  if (company !== siteConfig.demoCompanyFolder) {
    return NextResponse.json({ detail: "Asset not found" }, { status: 404 });
  }
  return createDemoAssetResponse(assetPath);
}
