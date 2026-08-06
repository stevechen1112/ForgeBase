"use client";
import { useEffect, useState, useCallback, useMemo } from "react";
import Link from "next/link";
import { useAuth } from "@/lib/auth/store";
import { faqsApi, type FAQItem } from "@/lib/api/content";
import { Button } from "@/components/ui/button";
import { Plus } from "lucide-react";
import { DataTable } from "@/components/ui/DataTable";
import { Pagination } from "@/components/ui/Pagination";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { PublishToggle } from "@/components/ui/PublishToggle";

export default function FAQsListPage() {
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";
  const [rows, setRows] = useState<FAQItem[]>([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [tagFilter, setTagFilter] = useState("");
  const [localeFilter, setLocaleFilter] = useState("");

  const load = useCallback(() => {
    const params: Record<string, string | number> = { page, page_size: 20 };
    if (localeFilter) params.locale = localeFilter;
    faqsApi.list(token, params).then((res) => {
      setRows(res.data); setTotalPages(res.meta.total_pages);
    });
  }, [token, page, localeFilter]);

  useEffect(() => { load(); }, [load]);

  const handleDelete = async (id: string) => {
    setDeleting(id);
    await faqsApi.delete(token, id);
    load(); setDeleting(null);
  };

  const handleStatusChange = (id: string, newStatus: string) => {
    setRows((prev) => prev.map((r) => (r.id === id ? { ...r, status: newStatus } : r)));
  };

  const uniqueTags = useMemo(
    () => Array.from(new Set(rows.map((r) => r.category_tag).filter(Boolean))).sort() as string[],
    [rows]
  );

  const filteredRows = useMemo(
    () => (tagFilter ? rows.filter((r) => r.category_tag === tagFilter) : rows),
    [rows, tagFilter]
  );

  const COLUMNS = [
    {
      key: "question",
      label: "問題",
      render: (v: unknown) => (
        <p className="line-clamp-2 max-w-sm text-sm leading-snug">{String(v ?? "")}</p>
      ),
    },
    {
      key: "category_tag",
      label: "標籤",
      className: "w-32",
      render: (v: unknown) => (
        <span className="inline-flex rounded-full bg-blue-50 px-2 py-0.5 text-xs font-medium text-blue-700">
          {String(v ?? "")}
        </span>
      ),
    },
    { key: "locale", label: "語言", className: "w-20" },
    {
      key: "status", label: "狀態", className: "w-36",
      render: (_v: unknown, row: FAQItem) => (
        <div className="flex items-center gap-2">
          <StatusBadge status={row.status} />
          <PublishToggle
            entity="faqs"
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
          <h1 className="text-2xl font-bold tracking-tight">常見問題</h1>
          <p className="mt-1 text-sm text-muted-foreground">維護常見問答，可顯示在產品頁與應用頁，也有助搜尋引擎理解</p>
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
          <select
            value={tagFilter}
            onChange={(e) => setTagFilter(e.target.value)}
            className="rounded border border-gray-300 px-3 py-1.5 text-sm text-gray-700 bg-white"
          >
            <option value="">全部標籤</option>
            {uniqueTags.map((tag) => (
              <option key={tag} value={tag}>{tag}</option>
            ))}
          </select>
          <Button asChild><Link href="/dashboard/faqs/new"><Plus className="mr-1.5 h-4 w-4" />+ 新增常見問題</Link></Button>
        </div>
      </div>
      <DataTable columns={COLUMNS} rows={filteredRows} editBasePath="/dashboard/faqs" onDelete={handleDelete} isDeleting={deleting} />
      <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
    </div>
  );
}
