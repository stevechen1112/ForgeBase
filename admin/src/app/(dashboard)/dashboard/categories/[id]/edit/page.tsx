"use client";
import { useParams } from "next/navigation";
import { categoriesApi, type ProductCategory } from "@/lib/api/content";
import { useEntityEditorData } from "@/lib/useEntityEditorData";
import CategoryForm from "../../CategoryForm";

export default function EditCategoryPage() {
  const { id } = useParams<{ id: string }>();
  const { data, error, loading } = useEntityEditorData<ProductCategory>(id, categoriesApi.get);

  if (loading) return <p className="text-sm text-muted-foreground">載入中…</p>;
  if (error) return <p className="text-sm text-red-500">{error}</p>;
  if (!data) return null;

  return (
    <div>
      <h1 className="mb-6 text-2xl font-semibold text-foreground">
        編輯分類：{data.category_name}
      </h1>
      <CategoryForm initial={data} id={id} />
    </div>
  );
}
