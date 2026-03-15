"use client";
/**
 * 2.5.1 Page-level Analytics Dashboard
 * /dashboard/analytics/pages
 *
 * Shows per-page view counts and unique visitor counts for the selected date range.
 */
import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth/store";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

type PageRow = {
  page_type: string | null;
  page_id: string | null;
  page_url: string;
  views: number;
  unique_visitors: number;
};

type EntityRow = {
  page_type: string;
  page_id: string;
  page_url: string;
  page_view: number;
  rfq_start: number;
  rfq_submit: number;
  spec_download: number;
  cta_click: number;
};

export default function PageAnalyticsDashboard() {
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";

  const [days, setDays] = useState(30);
  const [tab, setTab] = useState<"pages" | "entities">("pages");
  const [pages, setPages] = useState<PageRow[]>([]);
  const [entities, setEntities] = useState<EntityRow[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!token) return;
    setLoading(true);

    const headers = { Authorization: `Bearer ${token}` };

    Promise.all([
      fetch(`${API_BASE}/tracking/events/pages?days=${days}`, { headers }).then((r) => r.json()),
      fetch(`${API_BASE}/tracking/events/entities?days=${days}`, { headers }).then((r) => r.json()),
    ])
      .then(([pagesData, entitiesData]) => {
        setPages(Array.isArray(pagesData) ? pagesData : []);
        setEntities(Array.isArray(entitiesData) ? entitiesData : []);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [token, days]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">頁面成效分析</h1>
          <p className="text-sm text-gray-500 mt-1">Page &amp; entity-level traffic breakdown</p>
        </div>

        {/* Date range selector */}
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

      {/* Tab switcher */}
      <div className="flex gap-2 border-b border-gray-200">
        {(["pages", "entities"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              tab === t
                ? "border-blue-600 text-blue-600"
                : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            {t === "pages" ? "全部頁面" : "實體成效（產品/應用）"}
          </button>
        ))}
      </div>

      {loading ? (
        <p className="text-center py-10 text-gray-400">Loading…</p>
      ) : tab === "pages" ? (
        <PageTable rows={pages} />
      ) : (
        <EntityTable rows={entities} />
      )}
    </div>
  );
}

function PageTable({ rows }: { rows: PageRow[] }) {
  if (rows.length === 0) return <p className="text-center py-10 text-gray-400">No data</p>;
  return (
    <div className="overflow-hidden rounded-xl border border-gray-200">
      <table className="w-full text-sm">
        <thead className="bg-gray-50 text-gray-600">
          <tr>
            <th className="py-3 px-4 text-left font-medium">Page URL</th>
            <th className="py-3 px-4 text-left font-medium">Type</th>
            <th className="py-3 px-4 text-right font-medium">Views</th>
            <th className="py-3 px-4 text-right font-medium">Unique Visitors</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {rows.map((r, i) => (
            <tr key={i} className="bg-white even:bg-gray-50 hover:bg-blue-50/40 transition-colors">
              <td className="py-3 px-4 text-gray-700 max-w-xs truncate">
                <a href={r.page_url} target="_blank" rel="noreferrer" className="hover:underline text-blue-600">
                  {r.page_url}
                </a>
              </td>
              <td className="py-3 px-4">
                <span className="inline-block rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600">
                  {r.page_type ?? "—"}
                </span>
              </td>
              <td className="py-3 px-4 text-right font-mono">{r.views.toLocaleString()}</td>
              <td className="py-3 px-4 text-right font-mono">{r.unique_visitors.toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function EntityTable({ rows }: { rows: EntityRow[] }) {
  if (rows.length === 0) return <p className="text-center py-10 text-gray-400">No data</p>;
  return (
    <div className="overflow-hidden rounded-xl border border-gray-200">
      <table className="w-full text-sm">
        <thead className="bg-gray-50 text-gray-600">
          <tr>
            <th className="py-3 px-4 text-left font-medium">Page</th>
            <th className="py-3 px-4 text-left font-medium">Type</th>
            <th className="py-3 px-4 text-right font-medium">Views</th>
            <th className="py-3 px-4 text-right font-medium">RFQ Starts</th>
            <th className="py-3 px-4 text-right font-medium">RFQ Submit</th>
            <th className="py-3 px-4 text-right font-medium">Downloads</th>
            <th className="py-3 px-4 text-right font-medium">CTA Clicks</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {rows.map((r, i) => (
            <tr key={i} className="bg-white even:bg-gray-50 hover:bg-blue-50/40 transition-colors">
              <td className="py-3 px-4 text-gray-700 max-w-xs truncate">
                <a href={r.page_url} target="_blank" rel="noreferrer" className="hover:underline text-blue-600">
                  {r.page_url || r.page_id}
                </a>
              </td>
              <td className="py-3 px-4">
                <span className="inline-block rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600">
                  {r.page_type}
                </span>
              </td>
              <td className="py-3 px-4 text-right font-mono">{r.page_view.toLocaleString()}</td>
              <td className="py-3 px-4 text-right font-mono">{r.rfq_start.toLocaleString()}</td>
              <td className="py-3 px-4 text-right font-mono">{r.rfq_submit.toLocaleString()}</td>
              <td className="py-3 px-4 text-right font-mono">{r.spec_download.toLocaleString()}</td>
              <td className="py-3 px-4 text-right font-mono">{r.cta_click.toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
