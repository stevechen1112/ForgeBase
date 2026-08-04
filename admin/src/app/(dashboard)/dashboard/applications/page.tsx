"use client";
import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { useAuth } from "@/lib/auth/store";
import { applicationsApi, type Application } from "@/lib/api/content";
import { Button } from "@/components/ui/button";
import { Plus } from "lucide-react";
import { DataTable } from "@/components/ui/DataTable";
import { Pagination } from "@/components/ui/Pagination";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { PublishToggle } from "@/components/ui/PublishToggle";

export default function ApplicationsListPage() {
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";
  const [rows, setRows] = useState<Application[]>([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [localeFilter, setLocaleFilter] = useState("");

  const load = useCallback(() => {
    const params: Record<string, string | number> = { page, page_size: 20 };
    if (localeFilter) params.locale = localeFilter;
    applicationsApi.list(token, params).then((res) => {
      setRows(res.data); setTotalPages(res.meta.total_pages);
    });
  }, [token, page, localeFilter]);

  useEffect(() => { load(); }, [load]);

  const handleDelete = async (id: string) => {
    setDeleting(id);
    await applicationsApi.delete(token, id);
    load(); setDeleting(null);
  };

  const handleStatusChange = (id: string, newStatus: string) => {
    setRows((prev) => prev.map((r) => (r.id === id ? { ...r, status: newStatus } : r)));
  };

  const INDUSTRY_COLORS: Record<string, string> = {
    "Automotive Aftermarket": "bg-blue-100 text-blue-700",
    "Industrial Maintenance": "bg-orange-100 text-orange-700",
    "Electrical Services": "bg-yellow-100 text-yellow-700",
    "Workshop Operations": "bg-green-100 text-green-700",
    "Private Label and Distribution": "bg-purple-100 text-purple-700",
    "Field Service": "bg-teal-100 text-teal-700",
  };

  const COLUMNS = [
    { key: "application_name", label: "應用場景名稱" },
    {
      key: "industry",
      label: "產業",
      render: (v: unknown) => {
        const name = String(v ?? "");
        const cls = INDUSTRY_COLORS[name] ?? "bg-gray-100 text-gray-600";
        return <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${cls}`}>{name}</span>;
      },
    },
    { key: "locale", label: "語言", className: "w-20" },
    {
      key: "status", label: "狀態", className: "w-36",
      render: (_v: unknown, row: Application) => (
        <div className="flex items-center gap-2">
          <StatusBadge status={row.status} />
          <PublishToggle
            entity="applications"
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
          <h1 className="text-2xl font-bold tracking-tight">應用場景</h1>
          <p className="mt-1 text-sm text-muted-foreground">管理產業應用場景文案，並連結相關產品與常見問題</p>
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
            <option value="zh-cn">简体中文</option>
            <option value="ja">日本語</option>
            <option value="ko">한국어</option>
            <option value="de">Deutsch</option>
          </select>
          <Button asChild><Link href="/dashboard/applications/new"><Plus className="mr-1.5 h-4 w-4" />+ 新增應用場景</Link></Button>
        </div>
      </div>
      <DataTable columns={COLUMNS} rows={rows} editBasePath="/dashboard/applications" onDelete={handleDelete} isDeleting={deleting} />
      <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
    </div>
  );
}
