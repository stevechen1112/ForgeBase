"use client";
import { useEffect, useState, useCallback } from "react";
import { useAuth } from "@/lib/auth/store";
import { pagesApi, type Page } from "@/lib/api/content";
import { DataTable } from "@/components/ui/DataTable";
import { Pagination } from "@/components/ui/Pagination";
import { StatusBadge } from "@/components/ui/StatusBadge";

const PAGE_TYPE_LABELS: Record<string, string> = {
  home: "首頁",
  about: "關於我們",
  contact: "聯絡我們",
  landing: "活動頁",
  campaign: "行銷活動",
  custom: "自訂",
};

const COLUMNS = [
  { key: "title", label: "頁面標題" },
  {
    key: "page_type",
    label: "類型",
    className: "w-32",
    render: (_v: unknown, row: Page) => PAGE_TYPE_LABELS[row.page_type] ?? row.page_type,
  },
  { key: "locale", label: "語言", className: "w-20" },
  { key: "status", label: "狀態", className: "w-28", render: (_v: unknown, row: Page) => <StatusBadge status={row.status} /> },
];

export default function PagesListPage() {
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";
  const [rows, setRows] = useState<Page[]>([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [localeFilter, setLocaleFilter] = useState("");

  const load = useCallback(() => {
    const params: Record<string, string | number> = { page, page_size: 20 };
    if (localeFilter) params.locale = localeFilter;
    pagesApi.list(token, params).then((res) => {
      setRows(res.data); setTotalPages(res.meta.total_pages);
    });
  }, [token, page, localeFilter]);

  useEffect(() => { load(); }, [load]);

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">頁面管理</h1>
          <p className="mt-1 text-sm text-muted-foreground">更新既有頁面的文字、圖片與內容狀態；網址與網站結構由 ForgeBase 團隊維護</p>
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
        </div>
      </div>
      <DataTable columns={COLUMNS} rows={rows} editBasePath="/dashboard/pages" />
      <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
    </div>
  );
}
