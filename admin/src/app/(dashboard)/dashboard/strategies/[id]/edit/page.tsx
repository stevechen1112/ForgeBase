"use client";
import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth/store";
import { strategiesApi, type ContentStrategy } from "@/lib/api/content";

const PAGE_TYPES = ["product", "application", "category", "faq", "comparison", "certification", "page", "other"];
const PAGE_TYPE_LABELS: Record<string, string> = {
  product: "商品",
  application: "應用場景",
  category: "商品分類",
  faq: "常見問題",
  comparison: "比較",
  certification: "認證",
  page: "頁面",
  other: "其他",
};
const STATUSES: ContentStrategy["status"][] = ["unplanned", "brief_created", "ai_generated", "in_review", "published"];
const STATUS_LABELS: Record<string, string> = {
  unplanned: "未規劃",
  brief_created: "大綱已建",
  ai_generated: "AI 已生成",
  in_review: "審核中",
  published: "已發布",
};

export default function EditStrategyPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";

  const [form, setForm] = useState({
    page_type: "product",
    entity_type: "",
    entity_id: "",
    brief_id: "",
    status: "unplanned" as ContentStrategy["status"],
    locale: "zh-TW",
    notes: "",
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    strategiesApi.get(token, id).then(({ data }) => {
      setForm({
        page_type: data.page_type,
        entity_type: data.entity_type ?? "",
        entity_id: data.entity_id ?? "",
        brief_id: data.brief_id ?? "",
        status: data.status,
        locale: data.locale,
        notes: data.notes ?? "",
      });
      setLoading(false);
    });
  }, [id, token]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const payload = Object.fromEntries(
        Object.entries(form).map(([k, v]) => [k, v === "" ? null : v])
      );
      await strategiesApi.update(token, id, payload);
      router.push("/dashboard/strategies");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "儲存失敗");
      setSaving(false);
    }
  };

  if (loading) return <p className="text-sm text-muted-foreground p-6">載入中…</p>;

  return (
    <div className="max-w-2xl space-y-6">
      <div>
        <Link href="/dashboard/strategies" className="text-xs text-muted-foreground hover:underline">← 返回內容策略</Link>
        <h1 className="text-2xl font-semibold text-foreground mt-2">編輯內容策略</h1>
      </div>

      <form onSubmit={handleSubmit} className="space-y-5 rounded-xl border border-gray-200 bg-white p-6">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-foreground mb-1">頁面類型 *</label>
            <select
              value={form.page_type}
              onChange={(e) => setForm({ ...form, page_type: e.target.value })}
              className="w-full rounded-md border border-input px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {PAGE_TYPES.map((t) => <option key={t} value={t}>{PAGE_TYPE_LABELS[t] ?? t}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-foreground mb-1">狀態 *</label>
            <select
              value={form.status}
              onChange={(e) => setForm({ ...form, status: e.target.value as ContentStrategy["status"] })}
              className="w-full rounded-md border border-input px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {STATUSES.map((s) => <option key={s} value={s}>{STATUS_LABELS[s]}</option>)}
            </select>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-foreground mb-1">內容類型</label>
            <input
              type="text"
              value={form.entity_type}
              onChange={(e) => setForm({ ...form, entity_type: e.target.value })}
              className="w-full rounded-md border border-input px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-foreground mb-1">內容編號</label>
            <input
              type="text"
              value={form.entity_id}
              onChange={(e) => setForm({ ...form, entity_id: e.target.value })}
              className="w-full rounded-md border border-input px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-foreground mb-1">寫作大綱編號</label>
            <input
              type="text"
              value={form.brief_id}
              onChange={(e) => setForm({ ...form, brief_id: e.target.value })}
              className="w-full rounded-md border border-input px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-foreground mb-1">語言</label>
            <select
              value={form.locale}
              onChange={(e) => setForm({ ...form, locale: e.target.value })}
              className="w-full rounded-md border border-input px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {["zh-TW", "zh-CN", "en"].map((l) => <option key={l} value={l}>{l}</option>)}
            </select>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-foreground mb-1">備註</label>
          <textarea
            rows={3}
            value={form.notes}
            onChange={(e) => setForm({ ...form, notes: e.target.value })}
            className="w-full rounded-md border border-input px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
          />
        </div>

        {error && <p className="text-sm text-red-600">{error}</p>}

        <div className="flex gap-3 pt-2">
          <button
            type="submit"
            disabled={saving}
            className="rounded-md bg-blue-700 px-5 py-2 text-sm font-medium text-white hover:bg-blue-800 transition-colors disabled:opacity-50"
          >
            {saving ? "儲存中…" : "儲存變更"}
          </button>
          <Link
            href="/dashboard/strategies"
            className="rounded-md border border-input px-5 py-2 text-sm font-medium text-foreground hover:bg-muted/50 transition-colors"
          >
            取消
          </Link>
        </div>
      </form>
    </div>
  );
}
