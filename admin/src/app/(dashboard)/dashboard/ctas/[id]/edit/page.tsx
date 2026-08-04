"use client";
import { useParams } from "next/navigation";
import { ctasApi, type CTA } from "@/lib/api/content";
import { useEntityEditorData } from "@/lib/useEntityEditorData";
import CTAForm from "../../CTAForm";

export default function EditCTAPage() {
  const { id } = useParams<{ id: string }>();
  const { data, error, loading } = useEntityEditorData<CTA>(id, ctasApi.get);

  if (loading) return <p className="text-sm text-muted-foreground">載入中…</p>;
  if (error) return <p className="text-sm text-red-500">{error}</p>;
  if (!data) return null;

  return (
    <div>
      <h1 className="mb-6 text-2xl font-semibold text-foreground">編輯行動按鈕：{data.cta_key}</h1>
      <CTAForm initial={data} id={id} />
    </div>
  );
}
