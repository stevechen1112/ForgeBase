import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/lib/auth/store";

export const metadata: Metadata = {
  title: "NorthForge Admin",
  robots: { index: false, follow: false },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-TW">
      <body>
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
