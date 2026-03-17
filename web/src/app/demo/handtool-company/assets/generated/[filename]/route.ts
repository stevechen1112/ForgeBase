import { createDemoAssetResponse } from "@/lib/demoAssetRoute";

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ filename: string }> },
) {
  const { filename } = await params;
  return createDemoAssetResponse(["generated", filename]);
}