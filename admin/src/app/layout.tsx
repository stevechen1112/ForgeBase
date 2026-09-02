import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/lib/auth/store";

export const metadata: Metadata = {
  title: "ForgeBase｜完整外銷營運後台",
  description: "為外銷業務團隊設計的網站、訪客與詢價承接工作區",
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
