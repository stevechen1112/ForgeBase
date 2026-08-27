import { revalidatePath } from "next/cache";
import { NextRequest, NextResponse } from "next/server";

/**
 * On-demand revalidate（CF→FB Publish Contract §8）
 *
 * ForgeBase API 在 publish / update / meta 修復 / unpublish 後呼叫：
 *   POST /api/revalidate
 *   headers: x-revalidate-secret: <REVALIDATE_SECRET>
 *   body: { "paths": ["/blog/<slug>", "/blog", ...] }
 */
export async function POST(request: NextRequest) {
  const expected = process.env.REVALIDATE_SECRET;
  const provided = request.headers.get("x-revalidate-secret");
  if (!expected || provided !== expected) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  let body: { paths?: unknown; layouts?: unknown };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON" }, { status: 400 });
  }

  const sanitize = (value: unknown) =>
    Array.isArray(value)
      ? value.filter(
          (item): item is string => typeof item === "string" && item.startsWith("/") && !item.startsWith("//"),
        )
      : [];
  const paths = sanitize(body.paths);
  const layouts = sanitize(body.layouts);
  if (paths.length === 0 && layouts.length === 0) {
    return NextResponse.json({ error: "paths or layouts required" }, { status: 422 });
  }

  for (const path of paths.slice(0, 50)) {
    revalidatePath(path);
  }
  for (const path of layouts.slice(0, 20)) {
    revalidatePath(path, "layout");
  }
  return NextResponse.json({ revalidated: true, paths, layouts });
}
