"use client";
import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { useAuth } from "@/lib/auth/store";
import { comparisonsApi, type ComparisonTopic } from "@/lib/api/content";
import { Button } from "@/components/ui/button";
import { Plus } from "lucide-react";
import { DataTable } from "@/components/ui/DataTable";
import { Pagination } from "@/components/ui/Pagination";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { PublishToggle } from "@/components/ui/PublishToggle";

export default function ComparisonsListPage() {
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";
  const [rows, setRows] = useState<ComparisonTopic[]>([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [localeFilter, setLocaleFilter] = useState("");

  const load = useCallback(() => {
    const params: Record<string, string | number> = { page, page_size: 20 };
    if (localeFilter) params.locale = localeFilter;
    comparisonsApi.list(token, params).then((res) => {
      setRows(res.data); setTotalPages(res.meta.total_pages);
    });
  }, [token, page, localeFilter]);

  useEffect(() => { load(); }, [load]);

  const handleDelete = async (id: string) => {
    if (!confirm("確定刪除？")) return;
    setDeleting(id);
    await comparisonsApi.delete(token, id);
    load(); setDeleting(null);
  };

  const handleStatusChange = (id: string, newStatus: string) => {
    setRows((prev) => prev.map((r) => (r.id === id ? { ...r, status: newStatus } : r)));
  };

  const COLUMNS = [
    { key: "topic_title", label: "競品比較主題" },
    { key: "slug", label: "網址路徑", className: "w-44 font-mono text-xs" },
    { key: "locale", label: "語言", className: "w-20" },
    {
      key: "status", label: "狀態", className: "w-36",
      render: (_v: unknown, row: ComparisonTopic) => (
        <div className="flex items-center gap-2">
          <StatusBadge status={row.status} />
          <PublishToggle
            entity="comparisons"
            id={row.id}
            currentStatus={row.status}
            onStatusChange={(s) => handleStatusChange(row.id, s)}
          />
        </div>
      ),
    },
  ];

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">競品比較</h1>
          <p className="mt-1 text-sm text-muted-foreground">維護競品比較主題，讓訪客清楚了解產品相對優勢，提升詢價意願</p>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={localeFilter}
            onChange={(e) => { setLocaleFilter(e.target.value); setPage(1); }}
            className="rounded border border-gray-300 px-3 py-1.5 text-sm text-gray-700 bg-white"
          >
            <option value="">全部語言</option>
            <option value="en">English</option>
            <option value="zh-tw">繁體中文</option>
          </select>
          <Button asChild><Link href="/dashboard/comparisons/new"><Plus className="mr-1.5 h-4 w-4" />+ 新增競品比較</Link></Button>
        </div>
      </div>
      <DataTable columns={COLUMNS} rows={rows} editBasePath="/dashboard/comparisons" onDelete={handleDelete} isDeleting={deleting} />
      <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
    </div>
  );
}
