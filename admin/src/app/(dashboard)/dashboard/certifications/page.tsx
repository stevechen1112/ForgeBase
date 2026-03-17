"use client";
import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { useAuth } from "@/lib/auth/store";
import { certificationsApi, type Certification } from "@/lib/api/content";
import { Button } from "@/components/ui/button";
import { Plus } from "lucide-react";
import { DataTable } from "@/components/ui/DataTable";
import { Pagination } from "@/components/ui/Pagination";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { PublishToggle } from "@/components/ui/PublishToggle";

export default function CertificationsListPage() {
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";
  const [rows, setRows] = useState<Certification[]>([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [deleting, setDeleting] = useState<string | null>(null);

  const load = useCallback(() => {
    certificationsApi.list(token, { page, page_size: 20 }).then((res) => {
      setRows(res.data); setTotalPages(res.meta.total_pages);
    });
  }, [token, page]);

  useEffect(() => { load(); }, [load]);

  const handleDelete = async (id: string) => {
    if (!confirm("確定刪除？")) return;
    setDeleting(id);
    await certificationsApi.delete(token, id);
    load(); setDeleting(null);
  };

  const handleStatusChange = (id: string, newStatus: string) => {
    setRows((prev) => prev.map((r) => (r.id === id ? { ...r, status: newStatus } : r)));
  };

  const COLUMNS = [
    { key: "cert_name", label: "認證名稱" },
    { key: "slug", label: "Slug", className: "w-48 font-mono text-xs" },
    { key: "issuer", label: "發行機構" },
    { key: "cert_number", label: "認證號碼", className: "w-36 font-mono text-xs" },
    { key: "locale", label: "語言", className: "w-20" },
    {
      key: "status", label: "狀態", className: "w-36",
      render: (_v: unknown, row: Certification) => (
        <div className="flex items-center gap-2">
          <StatusBadge status={row.status} />
          <PublishToggle
            entity="certifications"
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
          <h1 className="text-2xl font-bold tracking-tight">認證管理</h1>
          <p className="mt-1 text-sm text-muted-foreground">管理 ISO、RoHS、CE 等品質認證資料，展示於前台認證頁並支援 PDF 下載</p>
        </div>
        <Button asChild><Link href="/dashboard/certifications/new"><Plus className="mr-1.5 h-4 w-4" />+ 新增認證</Link></Button>
      </div>
      <DataTable columns={COLUMNS} rows={rows} editBasePath="/dashboard/certifications" onDelete={handleDelete} isDeleting={deleting} />
      <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
    </div>
  );
}
