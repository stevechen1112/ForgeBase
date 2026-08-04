"use client";
import { useParams } from "next/navigation";
import { briefsApi, type PageBrief } from "@/lib/api/content";
import { useEntityEditorData } from "@/lib/useEntityEditorData";
import BriefForm from "../../BriefForm";

export default function EditBriefPage() {
  const { id } = useParams<{ id: string }>();
  const { data, error, loading } = useEntityEditorData<PageBrief>(id, briefsApi.get);

  if (loading) return <p className="text-sm text-muted-foreground">載入中…</p>;
  if (error) return <p className="text-sm text-red-500">{error}</p>;
  if (!data) return null;

  return (
    <div>
      <h1 className="mb-6 text-2xl font-semibold text-foreground">編輯寫作大綱：{data.title_draft ?? data.target_page_type}</h1>
      <BriefForm initial={data} id={id} />
    </div>
  );
}
