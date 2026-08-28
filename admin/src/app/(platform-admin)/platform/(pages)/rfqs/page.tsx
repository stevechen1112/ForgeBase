"use client";

import { useCallback, useEffect, useState } from "react";
import { RefreshCw, Search, TriangleAlert } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { usePlatformAuth } from "@/lib/auth/platform-store";
import {
  platformAdminApi,
  type PlatformRFQItem,
} from "@/lib/api/platform-admin";

const STATUS_LABEL: Record<string, string> = {
  new: "新詢價",
  assigned: "已指派",
  in_progress: "處理中",
  quoted: "已報價",
  negotiation: "議價中",
  won: "成交",
  lost: "失單",
  expired: "逾期",
};

export default function PlatformRFQsPage() {
  const { state } = usePlatformAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";
  const [items, setItems] = useState<PlatformRFQItem[]>([]);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState("");
  const [attention, setAttention] = useState(true);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [classifyingId, setClassifyingId] = useState("");
  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError("");
    try {
      const result = await platformAdminApi.rfqs(token, {
        search: search || undefined,
        needs_attention: attention,
        limit: 200,
      });
      setItems(result.data);
      setTotal(result.total);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "無法讀取全平台 RFQ。");
    } finally {
      setLoading(false);
    }
  }, [token, search, attention]);
  useEffect(() => {
    const timer = window.setTimeout(() => void load(), 200);
    return () => window.clearTimeout(timer);
  }, [load]);
  async function classify(item: PlatformRFQItem, kind: "test" | "spam") {
    if (!token) return;
    const label = kind === "test" ? "測試資料" : "垃圾詢價";
    if (!window.confirm(`確認將 ${item.rfq_number} 標記為${label}？此動作會留下操作紀錄。`)) return;
    setClassifyingId(item.id); setError("");
    try {
      await platformAdminApi.classifyRfq(token, item.id, {
        ...(kind === "test" ? { is_test_data: true } : { is_spam: true }),
        reason: `平台人員從全平台詢價頁人工標記為${label}`,
      });
      await load();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "RFQ 分類失敗");
    } finally { setClassifyingId(""); }
  }
  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">全平台詢價</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            平台方只監控是否成功收件、指派與處理；不取代客戶業務，也不會從這裡自動聯繫訪客。
          </p>
        </div>
        <Button
          variant="outline"
          onClick={() => void load()}
          disabled={loading}
        >
          <RefreshCw
            className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`}
          />
          重新整理
        </Button>
      </div>
      {error && (
        <div className="rounded-lg border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
          {error}
        </div>
      )}
      <div className="flex flex-wrap gap-3 rounded-xl border bg-card p-4">
        <label className="relative min-w-[240px] flex-1">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="搜尋 RFQ、公司或聯絡人"
            className="pl-9"
          />
        </label>
        <label className="flex h-10 items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={attention}
            onChange={(event) => setAttention(event.target.checked)}
          />
          只看未指派或逾期
        </label>
      </div>
      <div className="overflow-hidden rounded-xl border bg-card shadow-sm">
        <div className="border-b px-5 py-3 text-sm text-muted-foreground">
          共 {total} 筆
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[1040px] text-sm">
            <thead>
              <tr className="border-b bg-muted/40 text-left text-xs text-muted-foreground">
                <th className="px-4 py-3">詢價</th>
                <th className="px-4 py-3">租戶</th>
                <th className="px-4 py-3">聯絡人</th>
                <th className="px-4 py-3">狀態</th>
                <th className="px-4 py-3">負責人</th>
                <th className="px-4 py-3">時間</th>
                <th className="px-4 py-3">資料治理</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr
                  key={item.id}
                  className="border-b last:border-0 hover:bg-muted/30"
                >
                  <td className="px-4 py-3">
                    <p className="font-medium">{item.rfq_number}</p>
                    <p className="text-xs text-muted-foreground">
                      品質 {item.quality_score} · {item.priority}
                    </p>
                  </td>
                  <td className="px-4 py-3">{item.tenant_name}</td>
                  <td className="px-4 py-3">
                    <p>{item.contact_name || "未提供"}</p>
                    <p className="text-xs text-muted-foreground">
                      {item.contact_email || ""}
                    </p>
                  </td>
                  <td className="px-4 py-3">
                    {item.sla_breached ? (
                      <span className="inline-flex items-center gap-1 text-red-700">
                        <TriangleAlert className="h-3.5 w-3.5" />
                        已逾期
                      </span>
                    ) : (
                      STATUS_LABEL[item.status] || item.status
                    )}
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">
                    {item.assigned_name || "未指派"}
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">
                    {new Date(item.created_at).toLocaleString("zh-TW")}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex gap-2">
                      <Button size="sm" variant="outline" disabled={classifyingId === item.id} onClick={() => void classify(item, "test")}>標記測試</Button>
                      <Button size="sm" variant="outline" disabled={classifyingId === item.id} onClick={() => void classify(item, "spam")}>標記垃圾</Button>
                    </div>
                  </td>
                </tr>
              ))}
              {!loading && !items.length && (
                <tr>
                  <td
                    colSpan={7}
                    className="px-4 py-12 text-center text-muted-foreground"
                  >
                    沒有符合條件的詢價。
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
