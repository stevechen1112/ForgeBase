"use client";
import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { useAuth } from "@/lib/auth/store";
import { briefsApi, type PageBrief } from "@/lib/api/content";
import { Button } from "@/components/ui/button";
import { Plus, Bot, CheckCircle2, Circle, Clock } from "lucide-react";
import { DataTable } from "@/components/ui/DataTable";
import { Pagination } from "@/components/ui/Pagination";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { pageTypeLabel } from "@/lib/content/displayLabels";
import { API_BASE, buildApiHeaders } from "@/lib/api/client";

const AI_STATUS_LABELS: Record<string, string> = {
  pending: "待處理",
  processing: "AI 生成中",
  done: "已完成",
  error: "錯誤",
};

const BRIEF_STATUS_LABELS: Record<string, string> = {
  draft: "草稿",
  approved: "已核准",
  done: "完成",
};

const BRIEF_STATUS_ICON: Record<string, React.ReactNode> = {
  draft: <Circle className="inline-block h-3.5 w-3.5 text-muted-foreground mr-1" />,
  approved: <CheckCircle2 className="inline-block h-3.5 w-3.5 text-emerald-500 mr-1" />,
  done: <CheckCircle2 className="inline-block h-3.5 w-3.5 text-blue-500 mr-1" />,
};

const COLUMNS = [
  {
    key: "target_page_type",
    label: "目標頁面類型",
    className: "w-40",
    render: (_v: unknown, row: PageBrief) => pageTypeLabel(row.target_page_type),
  },
  { key: "primary_keyword", label: "主要關鍵字" },
  { key: "locale", label: "語言", className: "w-20" },
  {
    key: "brief_status",
    label: "流程狀態",
    className: "w-36",
    render: (_v: unknown, row: PageBrief) => (
      <span className="inline-flex items-center text-sm">
        {BRIEF_STATUS_ICON[row.brief_status] ?? <Clock className="inline-block h-3.5 w-3.5 text-muted-foreground mr-1" />}
        {BRIEF_STATUS_LABELS[row.brief_status] ?? row.brief_status}
      </span>
    ),
  },
  {
    key: "ai_status",
    label: "AI 狀態",
    className: "w-32",
    render: (_v: unknown, row: PageBrief) => (
      <StatusBadge status={row.ai_status} labelMap={AI_STATUS_LABELS} />
    ),
  },
];

export default function BriefsListPage() {
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";
  const [rows, setRows] = useState<PageBrief[]>([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [triggering, setTriggering] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const load = useCallback(() => {
    briefsApi.list(token, { page, page_size: 20 }).then((res) => {
      setRows(res.data); setTotalPages(res.meta.total_pages);
    });
  }, [token, page]);

  useEffect(() => { load(); }, [load]);

  const handleDelete = async (id: string) => {
    if (!confirm("確定刪除此寫作大綱？")) return;
    setDeleting(id);
    await briefsApi.delete(token, id);
    load(); setDeleting(null);
  };

  const handleTriggerWorkflow = async (brief: PageBrief) => {
    if (brief.brief_status !== "draft") return;
    setTriggering(brief.id); setMessage(null);
    try {
      // Step 1: approve the brief
      const patchRes = await fetch(`${API_BASE}/content/briefs/${brief.id}`, {
        method: "PATCH",
        headers: buildApiHeaders(token, { "Content-Type": "application/json" }),
        body: JSON.stringify({ brief_status: "approved" }),
      });
      if (!patchRes.ok) throw new Error(`Approve failed: HTTP ${patchRes.status}`);
      // Step 2: trigger AI generation
      const genRes = await fetch(`${API_BASE}/content/generate`, {
        method: "POST",
        headers: buildApiHeaders(token, { "Content-Type": "application/json" }),
        body: JSON.stringify({ brief_id: brief.id, target_locale: brief.locale }),
      });
      if (!genRes.ok) throw new Error(`Generate failed: HTTP ${genRes.status}`);
      setMessage(`寫作大綱「${brief.primary_keyword ?? brief.id}」AI 產生流程已啟動 ✓`);
      load();
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "觸發失敗");
    } finally {
      setTriggering(null);
    }
  };

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">寫作大綱</h1>
          <p className="mt-1 text-sm text-muted-foreground">撰寫前先定義關鍵字、目標對象與內容方向</p>
        </div>
        <Button asChild><Link href="/dashboard/briefs/new"><Plus className="mr-1.5 h-4 w-4" />新增大綱</Link></Button>
      </div>

      {message && (
        <div className="mb-4 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-2.5 text-sm text-emerald-800 dark:border-emerald-900/40 dark:bg-emerald-950/20 dark:text-emerald-300">
          {message}
        </div>
      )}

      <DataTable
        columns={COLUMNS}
        rows={rows}
        editBasePath="/dashboard/briefs"
        onDelete={handleDelete}
        isDeleting={deleting}
        extraActions={(row: PageBrief) =>
          row.brief_status === "draft" ? (
            <Button
              size="sm"
              variant="outline"
              className="gap-1.5 text-xs"
              disabled={triggering === row.id}
              onClick={() => handleTriggerWorkflow(row)}
            >
              <Bot className="h-3.5 w-3.5" />
              {triggering === row.id ? "觸發中…" : "啟動 AI 產生"}
            </Button>
          ) : null
        }
      />
      <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
    </div>
  );
}
