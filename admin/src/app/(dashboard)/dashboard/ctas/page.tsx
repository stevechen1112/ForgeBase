"use client";
import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { useAuth } from "@/lib/auth/store";
import { ctasApi, type CTA } from "@/lib/api/content";
import { Button } from "@/components/ui/button";
import { Plus } from "lucide-react";
import { DataTable } from "@/components/ui/DataTable";
import { Pagination } from "@/components/ui/Pagination";
import { StatusBadge } from "@/components/ui/StatusBadge";

const COLUMNS = [
  { key: "cta_key", label: "Key", className: "font-mono text-xs w-40" },
  { key: "headline", label: "標題" },
  { key: "cta_type", label: "類型", className: "w-28" },
  { key: "locale", label: "語言", className: "w-20" },
  { key: "status", label: "狀態", className: "w-28", render: (_v: unknown, row: CTA) => <StatusBadge status={row.status} /> },
];

export default function CTAsListPage() {
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";
  const [rows, setRows] = useState<CTA[]>([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [deleting, setDeleting] = useState<string | null>(null);

  const load = useCallback(() => {
    ctasApi.list(token, { page, page_size: 20 }).then((res) => {
      setRows(res.data); setTotalPages(res.meta.total_pages);
    });
  }, [token, page]);

  useEffect(() => { load(); }, [load]);

  const handleDelete = async (id: string) => {
    if (!confirm("確定刪除？")) return;
    setDeleting(id);
    await ctasApi.delete(token, id);
    load(); setDeleting(null);
  };

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">CTA 管理</h1>
          <p className="mt-1 text-sm text-muted-foreground">管理全站行動呼籲模組，依受眾意圖與頁面類型動態顯示最合適的轉換入口</p>
        </div>
        <Button asChild><Link href="/dashboard/ctas/new"><Plus className="mr-1.5 h-4 w-4" />+ 新增 CTA</Link></Button>
      </div>
      <DataTable columns={COLUMNS} rows={rows} editBasePath="/dashboard/ctas" onDelete={handleDelete} isDeleting={deleting} />
      <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
    </div>
  );
}
