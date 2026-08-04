import { NextResponse } from "next/server";

/**
 * Demo-only quick login.
 * Enable with DEMO_QUICK_LOGIN=1 (and NEXT_PUBLIC_DEMO_QUICK_LOGIN=1 for the UI button).
 * Remove / disable both flags before public launch.
 */
export async function POST() {
  if (process.env.DEMO_QUICK_LOGIN !== "1") {
    return NextResponse.json(
      { detail: "Demo quick login is disabled" },
      { status: 404 }
    );
  }

  const email =
    process.env.DEMO_ADMIN_EMAIL?.trim() || "admin@forgebase.com";
  const password =
    process.env.DEMO_ADMIN_PASSWORD?.trim() || "ForgeBase_Admin_2026!";

  const apiBase = (
    process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1"
  ).replace(/\/$/, "");
  const loginUrl = apiBase.endsWith("/api/v1")
    ? `${apiBase}/auth/login`
    : `${apiBase}/api/v1/auth/login`;

  try {
    const upstream = await fetch(loginUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
      cache: "no-store",
    });

    const body = await upstream.json().catch(() => null);
    if (!upstream.ok) {
      return NextResponse.json(
        { detail: body?.detail || "Demo login failed" },
        { status: upstream.status }
      );
    }

    return NextResponse.json(body);
  } catch (err) {
    const message = err instanceof Error ? err.message : "Demo login unavailable";
    return NextResponse.json({ detail: message }, { status: 502 });
  }
}
