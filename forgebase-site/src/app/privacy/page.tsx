import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = { title: "資料使用說明｜ForgeBase", description: "ForgeBase 產品測試與導入評估期間的資料使用說明。" };

export default function PrivacyPage() {
  return <main className="legal-page section-shell"><Link href="/" className="text-cta legal-back">← 返回 ForgeBase</Link><span className="section-code">DATA USE NOTICE</span><h1>資料使用說明</h1><p>本說明適用於 ForgeBase 官網的導入評估申請，以及 ForgeBase 測試網站中的功能驗證資料。</p><h2>蒐集哪些資料</h2><p>導入評估表單可能蒐集公司名稱、產業、現有網站、聯絡人、公司 Email、電話、職稱、目標市場及需求說明；系統亦會保存申請時間、來源頁面與經雜湊處理的網路識別資料，用於防止濫用與問題追查。</p><h2>如何使用</h2><p>資料僅用於判斷 ForgeBase 產品測試與導入適配性、維護申請處理紀錄、確保系統安全，以及改善產品流程。送出資料不會自動建立帳號、啟動試用或成為已受理的銷售案件。</p><h2>對外聯繫</h2><p>產品測試期間，系統不會依申請資料自動寄送行銷郵件。若後續需要進一步確認，是否聯繫及聯繫方式將由 ForgeBase 團隊人工判斷。</p><h2>保存與權利</h2><p>資料僅在評估、測試、安全與必要稽核期間保存。正式對外測試前，ForgeBase 仍會補充確認營運主體、正式聯絡方式與適用的保存期限；若這些資料尚未公開，本頁不構成正式商業服務的完整隱私政策。</p><p className="legal-note">版本：2026-08-16（產品測試期間）</p></main>;
}
