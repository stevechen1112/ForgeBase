"use client";
import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { useAuth } from "@/lib/auth/store";
import { capabilitiesApi, type Capability } from "@/lib/api/content";
import { Button } from "@/components/ui/button";
import { Plus } from "lucide-react";
import { DataTable } from "@/components/ui/DataTable";
import { Pagination } from "@/components/ui/Pagination";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { PublishToggle } from "@/components/ui/PublishToggle";

const SELECT_CLS = "flex h-9 rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring text-foreground";

const TAG_COLORS: Record<string, string> = {
  OEM:       "bg-blue-50 text-blue-700",
  Packaging: "bg-purple-50 text-purple-700",
  Quality:   "bg-green-50 text-green-700",
  Assembly:  "bg-amber-50 text-amber-700",
  Export:    "bg-cyan-50 text-cyan-700",
};

export default function CapabilitiesListPage() {
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";
  const [rows, setRows] = useState<Capability[]>([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [localeFilter, setLocaleFilter] = useState("");

  const load = useCallback(() => {
    const params: Record<string, string | number> = { page, page_size: 20 };
    if (localeFilter) params.locale = localeFilter;
    capabilitiesApi.list(token, params).then((res) => {
      setRows(res.data); setTotalPages(res.meta.total_pages);
    });
  }, [token, page, localeFilter]);

  useEffect(() => { load(); }, [load]);

  const handleDelete = async (id: string) => {
    setDeleting(id);
    await capabilitiesApi.delete(token, id);
    load(); setDeleting(null);
  };

  const handleStatusChange = (id: string, newStatus: string) => {
    setRows((prev) => prev.map((r) => (r.id === id ? { ...r, status: newStatus } : r)));
  };

  const COLUMNS = [
    { key: "capability_name", label: "廠能名稱" },
    {
      key: "short_description", label: "簡短描述",
      render: (v: unknown) => (
        <span className="line-clamp-2 max-w-xs text-sm text-muted-foreground">{v as string}</span>
      ),
    },
    {
      key: "category_tag", label: "分類標籤", className: "w-28",
      render: (v: unknown) => {
        const tag = v as string | undefined;
        if (!tag) return <span className="text-muted-foreground text-xs">—</span>;
        const cls = TAG_COLORS[tag] ?? "bg-gray-50 text-gray-600";
        return <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${cls}`}>{tag}</span>;
      },
    },
    { key: "locale", label: "語言", className: "w-16" },
    { key: "sort_order", label: "排序", className: "w-16 text-center" },
    {
      key: "status", label: "狀態", className: "w-36",
      render: (_v: unknown, row: Capability) => (
        <div className="flex items-center gap-2">
          <StatusBadge status={row.status} />
          <PublishToggle
            entity="capabilities"
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
          <h1 className="text-2xl font-bold tracking-tight">廠能介紹</h1>
          <p className="mt-1 text-sm text-muted-foreground">管理工廠能力與服務說明，展示於官網以建立買家信任</p>
        </div>
        <div className="flex items-center gap-3">
          <select className={SELECT_CLS} value={localeFilter} onChange={(e) => { setLocaleFilter(e.target.value); setPage(1); }}>
            <option value="">全部語言</option>
            <option value="en">English</option>
            <option value="zh-tw">繁體中文</option>
          </select>
          <Button asChild><Link href="/dashboard/capabilities/new"><Plus className="mr-1.5 h-4 w-4" />+ 新增廠能</Link></Button>
        </div>
      </div>
      <DataTable columns={COLUMNS} rows={rows} editBasePath="/dashboard/capabilities" onDelete={handleDelete} isDeleting={deleting} />
      <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
    </div>
  );
}
