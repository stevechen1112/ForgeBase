"use client";
import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { useAuth } from "@/lib/auth/store";
import { categoriesApi, type ProductCategory } from "@/lib/api/content";
import { Button } from "@/components/ui/button";
import { Plus } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { DataTable, type Column } from "@/components/ui/DataTable";
import { Pagination } from "@/components/ui/Pagination";
import { StatusBadge } from "@/components/ui/StatusBadge";

const COLUMNS: Column<ProductCategory>[] = [
  { key: "category_name", label: "Name" },
  { key: "slug", label: "Slug", className: "font-mono text-xs text-gray-500" },
  {
    key: "status",
    label: "Status",
    render: (v) => <StatusBadge status={String(v)} />,
  },
  { key: "sort_order", label: "Order", className: "w-16 text-center" },
  { key: "locale", label: "Locale", className: "w-16" },
];

export default function CategoriesPage() {
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";

  const [rows, setRows] = useState<ProductCategory[]>([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<string | null>(null);

  const load = useCallback(async (p: number) => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const res = await categoriesApi.list(token, { page: p, page_size: 20 });
      setRows(res.data);
      setTotalPages(res.meta.total_pages);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => { load(page); }, [load, page]);

  const handleDelete = async (id: string) => {
    if (!confirm("Are you sure you want to delete this category?")) return;
    setDeleting(id);
    try {
      await categoriesApi.delete(token, id);
      await load(page);
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : "Delete failed");
    } finally {
      setDeleting(null);
    }
  };

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">商品分類</h1>
          <p className="mt-0.5 text-sm text-muted-foreground">管理商品分類樹狀結構，分類直接影響前台導覽選單與商品 URL 路徑</p>
        </div>
        <Button asChild><Link href="/dashboard/categories/new"><Plus className="mr-1.5 h-4 w-4" />+ 新增分類</Link></Button>
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
