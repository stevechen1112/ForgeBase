import CTAForm from "../CTAForm";
export const metadata = { title: "新增行動按鈕 — ForgeBase 管理後台" };
export default function NewCTAPage() {
  return (
    <div>
      <h1 className="mb-6 text-2xl font-semibold text-foreground">新增行動按鈕</h1>
      <CTAForm />
    </div>
  );
}
