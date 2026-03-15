import CategoryForm from "../CategoryForm";

export const metadata = { title: "新增分類 — NorthForge Admin" };

export default function NewCategoryPage() {
  return (
    <div>
      <h1 className="mb-6 text-2xl font-semibold text-foreground">新增商品分類</h1>
      <CategoryForm />
    </div>
  );
}
