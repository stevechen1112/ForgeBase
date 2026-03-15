"use client";
/**
 * 2.5.3 Strategy Map Performance View
 * /dashboard/analytics/strategy
 *
 * Overlays real traffic metrics onto the content strategy map.
 */
import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth/store";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

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
    fetch(`${API_BASE}/tracking/events/strategy-performance?days=${days}`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => r.json())
      .then((data) => setRows(Array.isArray(data) ? data : []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [token, days]);

  const filtered = filterStatus ? rows.filter((r) => r.status === filterStatus) : rows;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">策略地圖成效</h1>
          <p className="text-sm text-gray-500 mt-1">Content strategy entries overlaid with real traffic data</p>
        </div>
        <div className="flex gap-3">
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">All statuses</option>
            <option value="unplanned">Unplanned</option>
            <option value="brief_created">Brief Created</option>
            <option value="ai_generated">AI Generated</option>
            <option value="in_review">In Review</option>
            <option value="published">Published</option>
          </select>
          <select
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
            className="text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value={7}>Last 7 days</option>
            <option value={30}>Last 30 days</option>
            <option value={90}>Last 90 days</option>
          </select>
        </div>
      </div>

      {loading ? (
        <p className="text-center py-10 text-gray-400">Loading…</p>
      ) : filtered.length === 0 ? (
        <p className="text-center py-10 text-gray-400">No strategy entries found</p>
      ) : (
        <div className="overflow-hidden rounded-xl border border-gray-200">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-gray-600">
              <tr>
                <th className="py-3 px-4 text-left font-medium">Page Type</th>
                <th className="py-3 px-4 text-left font-medium">Entity</th>
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
