import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/lib/auth/store";

export const metadata: Metadata = {
  title: "ForgeBase 管理後台",
  robots: { index: false, follow: false },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-TW" data-scroll-behavior="smooth">
      <body>
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
