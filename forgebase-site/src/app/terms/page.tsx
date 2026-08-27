import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = { title: "產品測試說明｜ForgeBase", description: "ForgeBase 目前產品測試與導入評估的使用界線。" };

export default function TermsPage() {
  return (
    <main className="legal-page section-shell">
      <Link href="/" className="text-cta legal-back">← 返回 ForgeBase</Link>
      <span className="section-code">PRODUCT TEST NOTICE</span>
      <h1>產品測試說明</h1>
      <p>ForgeBase 目前開放的是產品介紹、功能測試與導入適配性評估，尚未在本網站公布正式銷售方案。</p>
      <h2>申請不等於承諾</h2>
      <p>送出導入評估申請，不代表 ForgeBase 已接受專案、提供免費試用、同意特定價格或承諾建站與交付時程。任何實際合作範圍均需另行確認。</p>
      <h2>展示內容</h2>
      <p>NorthForge Tools 與產業範本中的公司、設備、規格、證書、產能及成效數字均為測試情境，用於驗證完整網站與後台流程，不代表真實法人、工廠或供貨能力。</p>
      <h2>功能界線</h2>
      <p>AI 產品顧問是 ForgeBase 核心功能：依網站已發布內容回答問題、協助找產品，並引導完成詢價。顧問不報價、不保證交期，也不對認證適用性下最終結論。</p>
      <p>公司辨識、內容成長及部分第三方資料服務仍屬進階測試，可能尚未啟用或仍需外部供應商。網站上線本身不保證自然產生流量、詢價、lead 或成交。</p>
      <p className="legal-note">版本：2026-08-18（產品測試期間）</p>
    </main>
  );
}
