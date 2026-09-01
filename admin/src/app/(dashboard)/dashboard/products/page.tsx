"use client";
import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { useAuth } from "@/lib/auth/store";
import { productsApi, type Product } from "@/lib/api/content";
import { Button } from "@/components/ui/button";
import { Plus, Star, Loader2, ChevronUp, ChevronDown } from "lucide-react";
import { DataTable } from "@/components/ui/DataTable";
import { Pagination } from "@/components/ui/Pagination";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { PublishToggle } from "@/components/ui/PublishToggle";

export default function ProductsListPage() {
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";

  const [rows, setRows] = useState<Product[]>([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [featuringId, setFeaturingId] = useState<string | null>(null);
  const [sortingId, setSortingId] = useState<string | null>(null);
  const [localeFilter, setLocaleFilter] = useState("");
  const [pairStatus, setPairStatus] = useState("");

  useEffect(() => {
    const pair = new URLSearchParams(window.location.search).get("pair_status");
    if (pair) setPairStatus(pair);
  }, []);

  const load = useCallback(() => {
    const params: Record<string, string | number> = { page, page_size: 20 };
    if (localeFilter) params.locale = localeFilter;
    if (pairStatus) params.pair_status = pairStatus;
    productsApi.list(token, params).then((res) => {
      setRows(res.data);
      setTotalPages(res.meta.total_pages);
    });
  }, [token, page, localeFilter, pairStatus]);

  useEffect(() => { load(); }, [load]);

  const handleDelete = async (id: string) => {
    setDeleting(id);
    await productsApi.delete(token, id);
    load();
    setDeleting(null);
  };

  const handleStatusChange = (id: string, newStatus: string) => {
    setRows((prev) => prev.map((r) => (r.id === id ? { ...r, status: newStatus } : r)));
  };

  const handleToggleFeatured = async (id: string, current: boolean) => {
    setFeaturingId(id);
    try {
      await productsApi.update(token, id, { is_featured: !current } as Partial<Product>);
      setRows((prev) => prev.map((r) => (r.id === id ? { ...r, is_featured: !current } : r)));
    } finally {
      setFeaturingId(null);
    }
  };

  const handleBumpPriority = async (row: Product, delta: number) => {
    setSortingId(row.id);
    try {
      const next = Math.max(0, (row.display_priority || 0) + delta);
      await productsApi.update(token, row.id, { display_priority: next } as Partial<Product>);
      load();
    } finally {
      setSortingId(null);
    }
  };

  const COLUMNS = [
    { key: "product_name", label: "商品名稱" },
    { key: "model_number", label: "型號" },
    { key: "locale", label: "語言", className: "w-20" },
    {
      key: "display_priority",
      label: "排序",
      className: "w-24",
      render: (_v: unknown, row: Product) => (
        <div className="flex items-center gap-1">
          <span className="w-6 text-right text-xs tabular-nums text-muted-foreground">{row.display_priority}</span>
          <button type="button" className="rounded p-0.5 hover:bg-gray-100 disabled:opacity-50" disabled={sortingId === row.id} onClick={() => void handleBumpPriority(row, 1)} title="往前" aria-label="提高排序">
            {sortingId === row.id ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <ChevronUp className="h-3.5 w-3.5" />}
          </button>
          <button type="button" className="rounded p-0.5 hover:bg-gray-100 disabled:opacity-50" disabled={sortingId === row.id} onClick={() => void handleBumpPriority(row, -1)} title="往後" aria-label="降低排序">
            <ChevronDown className="h-3.5 w-3.5" />
          </button>
        </div>
      ),
    },
    {
      key: "is_featured",
      label: "主推",
      className: "w-16",
      render: (_v: unknown, row: Product) => (
        <button
          onClick={() => handleToggleFeatured(row.id, row.is_featured)}
          disabled={featuringId === row.id}
          className="p-1 rounded hover:bg-gray-100 transition-colors disabled:opacity-50"
          title={row.is_featured ? "取消主推" : "設為主推"}
        >
          {featuringId === row.id
            ? <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
            : <Star className={`h-4 w-4 ${row.is_featured ? "fill-amber-400 text-amber-400" : "text-gray-300"}`} />}
        </button>
      ),
    },
    {
      key: "status",
      label: "狀態",
      className: "w-36",
      render: (_v: unknown, row: Product) => (
        <div className="flex items-center gap-2">
          <StatusBadge status={row.status} />
          <PublishToggle
            entity="products"
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
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">商品管理</h1>
          <p className="mt-1 text-sm text-muted-foreground">管理產品型錄：規格、圖片、分類與多語內容。可用「客戶語言」找出缺英文、草稿未上架或需要更新的商品。</p>
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
            value={pairStatus}
            onChange={(e) => { setPairStatus(e.target.value); setPage(1); }}
            className="rounded border border-gray-300 px-3 py-1.5 text-sm text-gray-700 bg-white"
          >
            <option value="">客戶語言：全部</option>
            <option value="missing_target">缺客戶語言內容</option>
            <option value="draft_target">草稿未上架</option>
            <option value="stale">已過期需更新</option>
          </select>
          <Button asChild><Link href="/dashboard/products/new"><Plus className="mr-1.5 h-4 w-4" />+ 新增商品</Link></Button>
        </div>
      </div>
      <DataTable
        columns={COLUMNS}
        rows={rows}
        editBasePath="/dashboard/products"
        onDelete={handleDelete}
        isDeleting={deleting}
      />
      <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
    </div>
  );
}
