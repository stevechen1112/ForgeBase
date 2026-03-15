import PageContentForm from "../PageContentForm";
export const metadata = { title: "新增頁面 — NorthForge Admin" };
export default function NewPagePage() {
  return (
    <div>
      <h1 className="mb-6 text-2xl font-semibold text-foreground">新增頁面</h1>
      <PageContentForm />
    </div>
  );
}
