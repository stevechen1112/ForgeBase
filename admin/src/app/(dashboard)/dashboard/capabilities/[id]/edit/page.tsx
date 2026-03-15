"use client";
import { useParams } from "next/navigation";
import { capabilitiesApi, type Capability } from "@/lib/api/content";
import { useEntityEditorData } from "@/lib/useEntityEditorData";
import CapabilityForm from "../../CapabilityForm";

export default function EditCapabilityPage() {
  const { id } = useParams<{ id: string }>();
  const { data, error, loading } = useEntityEditorData<Capability>(id, capabilitiesApi.get);

  if (loading) return <p className="text-sm text-muted-foreground">載入中…</p>;
  if (error) return <p className="text-sm text-red-500">{error}</p>;
  if (!data) return null;

  return (
    <div>
      <h1 className="mb-6 text-2xl font-semibold text-foreground">編輯廠能：{data.capability_name}</h1>
      <CapabilityForm initial={data} id={id} />
    </div>
  );
}
