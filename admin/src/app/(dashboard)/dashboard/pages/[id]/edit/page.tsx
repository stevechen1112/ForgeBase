"use client";
import { useState } from "react";
import { useParams } from "next/navigation";
import { pagesApi, previewApi, type Page } from "@/lib/api/content";
import { useEntityEditorData } from "@/lib/useEntityEditorData";
import PageContentForm from "../../PageContentForm";
import { TrustCheckCard } from "@/components/content/TrustCheckCard";

export default function EditPagePage() {
  const { id } = useParams<{ id: string }>();
  const { data, error, loading, token } = useEntityEditorData<Page>(id, pagesApi.get);
  const [previewing, setPreviewing] = useState(false);

  const handlePreview = async () => {
    setPreviewing(true);
    try {
      const res = await previewApi.createToken(token, id);
      window.open(res.preview_url, "_blank", "noopener,noreferrer");
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : "無法產生預覽連結");
    } finally {
      setPreviewing(false);
    }
  };

  if (loading) return <p className="text-sm text-muted-foreground">載入中…</p>;
  if (error) return <p className="text-sm text-red-500">{error}</p>;
  if (!data) return null;

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-foreground">編輯頁面：{data.title}</h1>
        <button
          type="button"
          onClick={handlePreview}
          disabled={previewing}
          className="flex items-center gap-2 rounded-md border border-input bg-white px-4 py-2 text-sm font-medium text-foreground hover:bg-muted/50 disabled:opacity-50 transition-colors"
        >
          {previewing ? (
            "產生中…"
          ) : (
            <>
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
              </svg>
              預覽頁面
            </>
          )}
        </button>
      </div>
      <PageContentForm initial={data} id={id} />
      <TrustCheckCard pageId={id} />
    </div>
  );
}
