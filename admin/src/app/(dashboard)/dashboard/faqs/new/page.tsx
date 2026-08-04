import FAQForm from "../FAQForm";
export const metadata = { title: "新增常見問題 — NorthForge Admin" };
export default function NewFAQPage() {
  return (
    <div>
      <h1 className="mb-6 text-2xl font-semibold text-foreground">新增常見問題</h1>
      <FAQForm />
    </div>
  );
}
