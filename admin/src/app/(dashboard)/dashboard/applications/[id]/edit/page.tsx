"use client";
import { useParams } from "next/navigation";
import { applicationsApi, type Application } from "@/lib/api/content";
import { useEntityEditorData } from "@/lib/useEntityEditorData";
import ApplicationForm from "../../ApplicationForm";

export default function EditApplicationPage() {
  const { id } = useParams<{ id: string }>();
  const { data, error, loading } = useEntityEditorData<Application>(id, applicationsApi.get);

  if (loading) return <p className="text-sm text-muted-foreground">載入中…</p>;
  if (error) return <p className="text-sm text-red-500">{error}</p>;
  if (!data) return null;

  return (
    <div>
      <h1 className="mb-6 text-2xl font-semibold text-foreground">編輯應用場景：{data.application_name}</h1>
      <ApplicationForm initial={data} id={id} />
    </div>
  );
}
