"use client";
import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { useAuth } from "@/lib/auth/store";
import { pagesApi, type Page } from "@/lib/api/content";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Plus } from "lucide-react";
import { DataTable } from "@/components/ui/DataTable";
import { Pagination } from "@/components/ui/Pagination";
import { StatusBadge } from "@/components/ui/StatusBadge";

const PAGE_TYPE_LABELS: Record<string, string> = {
  home: "首頁",
  about: "關於我們",
  contact: "聯絡我們",
  landing: "活動頁",
  campaign: "行銷活動",
  custom: "自訂",
};

const COLUMNS = [
  { key: "title", label: "頁面標題" },
  {
    key: "page_type",
    label: "類型",
    className: "w-32",
    render: (_v: unknown, row: Page) => PAGE_TYPE_LABELS[row.page_type] ?? row.page_type,
  },
  { key: "slug", label: "網址路徑", className: "w-44 font-mono text-xs" },
  { key: "locale", label: "語言", className: "w-20" },
  {
    key: "noindex",
    label: "索引",
    className: "w-24",
    render: (_v: unknown, row: Page) =>
      row.noindex
        ? <Badge variant="outline" className="border-amber-400 text-amber-700 text-xs">不索引</Badge>
        : <Badge variant="outline" className="border-green-500 text-green-700 text-xs">可索引</Badge>,
  },
  {
    key: "structured_data",
    label: "結構化資料",
    className: "w-20",
    render: (_v: unknown, row: Page) =>
      row.structured_data
        ? <span className="text-xs text-green-600 font-medium">✓</span>
        : <span className="text-xs text-muted-foreground">—</span>,
  },
  { key: "status", label: "狀態", className: "w-28", render: (_v: unknown, row: Page) => <StatusBadge status={row.status} /> },
];

export default function PagesListPage() {
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";
  const [rows, setRows] = useState<Page[]>([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [deleting, setDeleting] = useState<string | null>(null);

  const load = useCallback(() => {
    pagesApi.list(token, { page, page_size: 20 }).then((res) => {
      setRows(res.data); setTotalPages(res.meta.total_pages);
    });
  }, [token, page]);

  useEffect(() => { load(); }, [load]);

  const handleDelete = async (id: string) => {
    if (!confirm("確定刪除？")) return;
    setDeleting(id);
    await pagesApi.delete(token, id);
    load(); setDeleting(null);
  };

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">頁面管理</h1>
          <p className="mt-1 text-sm text-muted-foreground">管理官網靜態頁與內容頁，可設多語與搜尋用標題／說明</p>
        </div>
        <Button asChild><Link href="/dashboard/pages/new"><Plus className="mr-1.5 h-4 w-4" />+ 新增頁面</Link></Button>
      </div>
      <DataTable columns={COLUMNS} rows={rows} editBasePath="/dashboard/pages" onDelete={handleDelete} isDeleting={deleting} />
      <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
    </div>
  );
}
