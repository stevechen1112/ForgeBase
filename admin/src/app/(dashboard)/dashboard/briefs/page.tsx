"use client";
import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { useAuth } from "@/lib/auth/store";
import { briefsApi, type PageBrief } from "@/lib/api/content";
import { Button } from "@/components/ui/button";
import { Plus } from "lucide-react";
import { DataTable } from "@/components/ui/DataTable";
import { Pagination } from "@/components/ui/Pagination";
import { StatusBadge } from "@/components/ui/StatusBadge";

const AI_STATUS_LABELS: Record<string, string> = {
  pending: "待處理",
  processing: "AI 生成中",
  done: "已完成",
  error: "錯誤",
};

const COLUMNS = [
  { key: "target_page_type", label: "目標頁面類型", className: "w-40" },
  { key: "primary_keyword", label: "主要關鍵字" },
  { key: "locale", label: "語言", className: "w-20" },
  {
    key: "ai_status",
    label: "AI 狀態",
    className: "w-32",
    render: (_v: unknown, row: PageBrief) => (
      <StatusBadge status={row.ai_status} labelMap={AI_STATUS_LABELS} />
    ),
  },
];

export default function BriefsListPage() {
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";
  const [rows, setRows] = useState<PageBrief[]>([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [deleting, setDeleting] = useState<string | null>(null);

  const load = useCallback(() => {
    briefsApi.list(token, { page, page_size: 20 }).then((res) => {
      setRows(res.data); setTotalPages(res.meta.total_pages);
    });
  }, [token, page]);

  useEffect(() => { load(); }, [load]);

  const handleDelete = async (id: string) => {
    if (!confirm("確定刪除此摘要？")) return;
    setDeleting(id);
    await briefsApi.delete(token, id);
    load(); setDeleting(null);
  };

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">內容摘要 (Briefs)</h1>
          <p className="mt-1 text-sm text-muted-foreground">為 AI 寫作提供前置規劃，定義目標關鍵字、受眾與內容策略方向</p>
        </div>
        <Button asChild><Link href="/dashboard/briefs/new"><Plus className="mr-1.5 h-4 w-4" />+ 新增摘要</Link></Button>
      </div>
      <DataTable columns={COLUMNS} rows={rows} editBasePath="/dashboard/briefs" onDelete={handleDelete} isDeleting={deleting} />
      <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
    </div>
  );
}
