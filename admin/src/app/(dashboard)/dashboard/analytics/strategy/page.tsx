"use client";
/**
 * 2.5.3 Strategy Map Performance View
 * /dashboard/analytics/strategy
 *
 * Overlays real traffic metrics onto the content strategy map.
 */
import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth/store";
import { apiClient } from "@/lib/api/client";

type StrategyRow = {
  id: string;
  page_type: string;
  entity_type: string | null;
  entity_id: string | null;
  status: string;
  locale: string;
  notes: string | null;
  page_view: number;
  rfq_start: number;
  rfq_submit: number;
  spec_download: number;
};

const STATUS_BADGE: Record<string, string> = {
  unplanned: "bg-gray-100 text-gray-600",
  brief_created: "bg-blue-100 text-blue-700",
  ai_generated: "bg-purple-100 text-purple-700",
  in_review: "bg-yellow-100 text-yellow-700",
  published: "bg-green-100 text-green-700",
};

export default function StrategyPerformancePage() {
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";

  const [days, setDays] = useState(30);
  const [rows, setRows] = useState<StrategyRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [filterStatus, setFilterStatus] = useState("");

  useEffect(() => {
    if (!token) return;
    setLoading(true);
    apiClient
      .get<StrategyRow[]>(`/tracking/events/strategy-performance?days=${days}`, token)
      .then((data) => setRows(Array.isArray(data) ? data : []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [token, days]);

  const filtered = filterStatus ? rows.filter((r) => r.status === filterStatus) : rows;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">內容策略成效</h1>
          <p className="text-sm text-gray-500 mt-1">對照內容策略與實際流量，評估主題帶來的買家成效</p>
        </div>
        <div className="flex gap-3">
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">全部狀態</option>
            <option value="unplanned">未規劃</option>
            <option value="brief_created">已有大綱</option>
            <option value="ai_generated">AI 已產生</option>
            <option value="in_review">審核中</option>
            <option value="published">已上架</option>
          </select>
          <select
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
            className="text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value={7}>近 7 天</option>
            <option value={30}>近 30 天</option>
            <option value={90}>近 90 天</option>
          </select>
        </div>
      </div>

      {loading ? (
        <p className="text-center py-10 text-gray-400">載入中…</p>
      ) : filtered.length === 0 ? (
        <p className="text-center py-10 text-gray-400">尚無內容策略資料</p>
      ) : (
        <div className="overflow-hidden rounded-xl border border-gray-200">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-gray-600">
              <tr>
                <th className="py-3 px-4 text-left font-medium">Page Type</th>
                <th className="py-3 px-4 text-left font-medium">內容類型</th>
                <th className="py-3 px-4 text-left font-medium">Status</th>
                <th className="py-3 px-4 text-left font-medium">Locale</th>
                <th className="py-3 px-4 text-right font-medium">Views</th>
                <th className="py-3 px-4 text-right font-medium">RFQ Start</th>
                <th className="py-3 px-4 text-right font-medium">RFQ Submit</th>
                <th className="py-3 px-4 text-right font-medium">Downloads</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {filtered.map((r) => (
                <tr key={r.id} className="bg-white even:bg-gray-50 hover:bg-blue-50/40 transition-colors">
                  <td className="py-3 px-4">
                    <span className="inline-block rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600">
                      {r.page_type}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-gray-600 text-xs font-mono truncate max-w-xs">
                    {r.entity_type ? `${r.entity_type}` : "—"}
                    {r.entity_id && (
                      <span className="ml-1 text-gray-400">{r.entity_id.slice(0, 8)}…</span>
                    )}
                  </td>
                  <td className="py-3 px-4">
                    <span className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_BADGE[r.status] ?? "bg-gray-100 text-gray-600"}`}>
                      {r.status}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-gray-500">{r.locale}</td>
                  <td className="py-3 px-4 text-right font-mono">
                    {r.page_view > 0 ? (
                      <span className="text-blue-600 font-semibold">{r.page_view.toLocaleString()}</span>
                    ) : (
                      <span className="text-gray-300">0</span>
                    )}
                  </td>
                  <td className="py-3 px-4 text-right font-mono text-gray-600">{r.rfq_start}</td>
                  <td className="py-3 px-4 text-right font-mono text-gray-600">{r.rfq_submit}</td>
                  <td className="py-3 px-4 text-right font-mono text-gray-600">{r.spec_download}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
