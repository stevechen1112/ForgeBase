"use client";
import { useParams } from "next/navigation";
import { faqsApi, type FAQItem } from "@/lib/api/content";
import { useEntityEditorData } from "@/lib/useEntityEditorData";
import FAQForm from "../../FAQForm";

export default function EditFAQPage() {
  const { id } = useParams<{ id: string }>();
  const { data, error, loading } = useEntityEditorData<FAQItem>(id, faqsApi.get);

  if (loading) return <p className="text-sm text-muted-foreground">載入中…</p>;
  if (error) return <p className="text-sm text-red-500">{error}</p>;
  if (!data) return null;

  return (
    <div>
      <h1 className="mb-6 text-2xl font-semibold text-foreground">編輯 FAQ</h1>
      <FAQForm initial={data} id={id} />
    </div>
  );
}
