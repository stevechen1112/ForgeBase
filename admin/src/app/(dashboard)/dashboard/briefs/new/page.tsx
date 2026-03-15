import BriefForm from "../BriefForm";
export const metadata = { title: "新增內容摘要 — NorthForge Admin" };
export default function NewBriefPage() {
  return (
    <div>
      <h1 className="mb-6 text-2xl font-semibold text-foreground">新增內容摘要 (Brief)</h1>
      <BriefForm />
    </div>
  );
}
