"use client";
import { useParams } from "next/navigation";
import { certificationsApi, type Certification } from "@/lib/api/content";
import { useEntityEditorData } from "@/lib/useEntityEditorData";
import CertificationForm from "../../CertificationForm";

export default function EditCertificationPage() {
  const { id } = useParams<{ id: string }>();
  const { data, error, loading } = useEntityEditorData<Certification>(id, certificationsApi.get);

  if (loading) return <p className="text-sm text-muted-foreground">載入中…</p>;
  if (error) return <p className="text-sm text-red-500">{error}</p>;
  if (!data) return null;

  return (
    <div>
      <h1 className="mb-6 text-2xl font-semibold text-foreground">編輯認證：{data.cert_name}</h1>
      <CertificationForm initial={data} id={id} />
    </div>
  );
}
