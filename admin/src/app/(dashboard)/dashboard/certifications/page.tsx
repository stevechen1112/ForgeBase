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

const SELECT_CLS = "flex h-9 rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring text-foreground";

function ExpiryCell({ expiresAt }: { expiresAt?: string | null }) {
  if (!expiresAt) return <span className="text-muted-foreground text-xs">—</span>;
  const d = new Date(expiresAt);
  const daysLeft = Math.ceil((d.getTime() - Date.now()) / 86400000);
  const label = d.toLocaleDateString("zh-TW", { year: "numeric", month: "2-digit", day: "2-digit" });
  if (daysLeft < 0) return <span className="text-xs font-medium text-red-600">{label} 已過期</span>;
  if (daysLeft <= 90) return <span className="text-xs font-medium text-amber-600">{label} ({daysLeft}天後)</span>;
  return <span className="text-xs text-muted-foreground">{label}</span>;
}

export default function CertificationsListPage() {
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";
  const [rows, setRows] = useState<Certification[]>([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [localeFilter, setLocaleFilter] = useState("");

  const load = useCallback(() => {
    const params: Record<string, unknown> = { page, page_size: 20 };
    if (localeFilter) params.locale = localeFilter;
    certificationsApi.list(token, params).then((res) => {
      setRows(res.data); setTotalPages(res.meta.total_pages);
    });
  }, [token, page, localeFilter]);

  useEffect(() => { load(); }, [load]);

  const handleDelete = async (id: string) => {
    setDeleting(id);
    await certificationsApi.delete(token, id);
    load(); setDeleting(null);
  };

  const handleStatusChange = (id: string, newStatus: string) => {
    setRows((prev) => prev.map((r) => (r.id === id ? { ...r, status: newStatus } : r)));
  };

  const COLUMNS = [
    { key: "cert_name", label: "認證名稱" },
    {
      key: "issuer", label: "發行機構",
      render: (v: unknown) => v
        ? <span className="inline-flex rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-700">{v as string}</span>
        : <span className="text-muted-foreground text-xs">—</span>,
    },
    { key: "cert_number", label: "認證號碼", className: "w-36 font-mono text-xs" },
    {
      key: "expires_at", label: "到期日", className: "w-36",
      render: (v: unknown) => <ExpiryCell expiresAt={v as string | undefined} />,
    },
    { key: "locale", label: "語言", className: "w-16" },
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
        <div className="flex items-center gap-3">
          <select className={SELECT_CLS} value={localeFilter} onChange={(e) => { setLocaleFilter(e.target.value); setPage(1); }}>
            <option value="">全部語言</option>
            <option value="en">English</option>
            <option value="zh-tw">繁體中文</option>
            <option value="zh-cn">简体中文</option>
            <option value="ja">日本語</option>
            <option value="ko">한국어</option>
            <option value="de">Deutsch</option>
          </select>
          <Button asChild><Link href="/dashboard/certifications/new"><Plus className="mr-1.5 h-4 w-4" />+ 新增認證</Link></Button>
        </div>
      </div>
      <DataTable columns={COLUMNS} rows={rows} editBasePath="/dashboard/certifications" onDelete={handleDelete} isDeleting={deleting} />
      <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
    </div>
  );
}
