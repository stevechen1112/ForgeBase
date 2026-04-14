"use client";
import { PlatformAuthProvider } from "@/lib/auth/platform-store";

/**
 * Platform admin route group layout — wraps all /platform/* routes
 * with an independent auth provider (separate from tenant auth).
 */
export default function PlatformRootLayout({ children }: { children: React.ReactNode }) {
  return <PlatformAuthProvider>{children}</PlatformAuthProvider>;
}
