import ComparisonForm from "../ComparisonForm";
export const metadata = { title: "新增競品比較 — NorthForge Admin" };
export default function NewComparisonPage() {
  return (
    <div>
      <h1 className="mb-6 text-2xl font-semibold text-foreground">新增競品比較</h1>
      <ComparisonForm />
    </div>
  );
}
