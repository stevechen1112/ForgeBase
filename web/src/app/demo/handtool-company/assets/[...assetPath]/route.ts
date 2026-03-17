import { createDemoAssetResponse } from "@/lib/demoAssetRoute";

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ assetPath: string[] }> },
) {
  const { assetPath } = await params;
  return createDemoAssetResponse(assetPath);
}
