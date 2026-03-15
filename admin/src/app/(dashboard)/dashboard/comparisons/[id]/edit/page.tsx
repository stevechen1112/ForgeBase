"use client";
import { useParams } from "next/navigation";
import { comparisonsApi, type ComparisonTopic } from "@/lib/api/content";
import { useEntityEditorData } from "@/lib/useEntityEditorData";
import ComparisonForm from "../../ComparisonForm";

export default function EditComparisonPage() {
  const { id } = useParams<{ id: string }>();
  const { data, error, loading } = useEntityEditorData<ComparisonTopic>(id, comparisonsApi.get);

  if (loading) return <p className="text-sm text-muted-foreground">載入中…</p>;
  if (error) return <p className="text-sm text-red-500">{error}</p>;
  if (!data) return null;

  return (
    <div>
      <h1 className="mb-6 text-2xl font-semibold text-foreground">編輯競品比較：{data.topic_title}</h1>
      <ComparisonForm initial={data} id={id} />
    </div>
  );
}
