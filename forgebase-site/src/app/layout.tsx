import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  metadataBase: new URL("https://pcbrm.tw"),
  title: "ForgeBase｜製造業的海外客戶接待與詢價平台",
  description:
    "ForgeBase 協助外銷製造業介紹產品、引導買主查找資料並留下完整詢價，再把需求交給真人業務處理。",
  openGraph: {
    title: "ForgeBase｜24 小時全年無休的線上全能業務",
    description:
      "從介紹產品、協助查找與回答基本問題，到收集詢價條件並交給真人業務接手。",
    type: "website",
    locale: "zh_TW",
    siteName: "ForgeBase",
  },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-Hant-TW">
      <body>{children}</body>
    </html>
  );
}
