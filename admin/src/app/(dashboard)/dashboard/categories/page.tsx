"use client";
import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { useAuth } from "@/lib/auth/store";
import { categoriesApi, type ProductCategory } from "@/lib/api/content";
import { Button } from "@/components/ui/button";
import { Plus } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { DataTable } from "@/components/ui/DataTable";
import { Pagination } from "@/components/ui/Pagination";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { PublishToggle } from "@/components/ui/PublishToggle";

export default function CategoriesPage() {
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";

  const [rows, setRows] = useState<ProductCategory[]>([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [localeFilter, setLocaleFilter] = useState("");

  const load = useCallback(async (p: number) => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const params: Record<string, string | number> = { page: p, page_size: 20 };
      // API defaults locale=en when omitted — 「全部語言」必須顯式傳 all
      params.locale = localeFilter || "all";
      const res = await categoriesApi.list(token, params);
      setRows(res.data);
      setTotalPages(res.meta.total_pages);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "載入失敗");
    } finally {
      setLoading(false);
    }
  }, [token, localeFilter]);

  useEffect(() => { load(page); }, [load, page]);

  const handleDelete = async (id: string) => {
    setDeleting(id);
    try {
      await categoriesApi.delete(token, id);
      await load(page);
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : "刪除失敗");
    } finally {
      setDeleting(null);
    }
  };

  const handleStatusChange = (id: string, newStatus: string) => {
    setRows((prev) => prev.map((r) => (r.id === id ? { ...r, status: newStatus } : r)));
  };

  const COLUMNS = [
    { key: "category_name", label: "分類名稱" },
    { key: "slug", label: "URL 路徑", className: "font-mono text-xs text-muted-foreground" },
    {
      key: "status",
      label: "狀態",
      className: "w-44",
      render: (_v: unknown, row: ProductCategory) => (
        <div className="flex items-center gap-2">
          <StatusBadge status={row.status} />
          <PublishToggle
            entity="categories"
            id={row.id}
            currentStatus={row.status}
            onStatusChange={(s) => handleStatusChange(row.id, s)}
          />
        </div>
      ),
    },
    { key: "sort_order", label: "排序", className: "w-16 text-center" },
    { key: "locale", label: "語言", className: "w-16" },
  ];

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">商品分類</h1>
          <p className="mt-0.5 text-sm text-muted-foreground">管理產品分類；會影響官網選單與產品頁路徑</p>
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
          <Button asChild><Link href="/dashboard/categories/new"><Plus className="mr-1.5 h-4 w-4" />+ 新增分類</Link></Button>
        </div>
      </div>

      {error && <Alert variant="destructive" className="mb-4"><AlertDescription>{error}</AlertDescription></Alert>}

      {loading ? (
        <div className="flex items-center justify-center py-16 text-muted-foreground">載入中…</div>
      ) : (
        <>
          <DataTable
            columns={COLUMNS}
            rows={rows}
            editBasePath="/dashboard/categories"
            onDelete={handleDelete}
            isDeleting={deleting}
          />
          <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
        </>
      )}
    </div>
  );
}
