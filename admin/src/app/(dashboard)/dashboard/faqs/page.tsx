"use client";
import { useEffect, useState, useCallback } from "react";
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

  const load = useCallback(() => {
    faqsApi.list(token, { page, page_size: 20 }).then((res) => {
      setRows(res.data); setTotalPages(res.meta.total_pages);
    });
  }, [token, page]);

  useEffect(() => { load(); }, [load]);

  const handleDelete = async (id: string) => {
    if (!confirm("確定刪除？")) return;
    setDeleting(id);
    await faqsApi.delete(token, id);
    load(); setDeleting(null);
  };

  const handleStatusChange = (id: string, newStatus: string) => {
    setRows((prev) => prev.map((r) => (r.id === id ? { ...r, status: newStatus } : r)));
  };

  const COLUMNS = [
    { key: "question", label: "問題" },
    { key: "category_tag", label: "標籤", className: "w-32" },
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
          <h1 className="text-2xl font-bold tracking-tight">FAQ 管理</h1>
          <p className="mt-1 text-sm text-muted-foreground">維護常見問題庫，支援商品頁與場景頁內嵌顯示，並產生 SEO 結構化標記</p>
        </div>
        <Button asChild><Link href="/dashboard/faqs/new"><Plus className="mr-1.5 h-4 w-4" />+ 新增 FAQ</Link></Button>
      </div>
      <DataTable columns={COLUMNS} rows={rows} editBasePath="/dashboard/faqs" onDelete={handleDelete} isDeleting={deleting} />
      <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
    </div>
  );
}
