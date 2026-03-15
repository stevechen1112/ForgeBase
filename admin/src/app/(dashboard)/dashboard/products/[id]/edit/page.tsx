"use client";
import { useParams } from "next/navigation";
import { productsApi, type Product } from "@/lib/api/content";
import { useEntityEditorData } from "@/lib/useEntityEditorData";
import ProductForm from "../../ProductForm";

export default function EditProductPage() {
  const { id } = useParams<{ id: string }>();
  const { data, error, loading } = useEntityEditorData<Product>(id, productsApi.get);

  if (loading) return <p className="text-sm text-muted-foreground">載入中…</p>;
  if (error) return <p className="text-sm text-red-500">{error}</p>;
  if (!data) return null;

  return (
    <div>
      <h1 className="mb-6 text-2xl font-semibold text-foreground">編輯商品：{data.product_name}</h1>
      <ProductForm initial={data} id={id} />
    </div>
  );
}
