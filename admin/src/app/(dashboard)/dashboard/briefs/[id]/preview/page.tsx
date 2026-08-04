"use client";
import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth/store";
import { briefsApi, type PageBrief } from "@/lib/api/content";
import { apiClient } from "@/lib/api/client";
import { StatusBadge } from "@/components/ui/StatusBadge";

type AILog = {
  id: string;
  model_name: string;
  status: string;
  output_json: unknown;
  error_message: string | null;
  created_at: string;
};

export default function BriefPreviewPage() {
  const { id } = useParams<{ id: string }>();
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";

  const [brief, setBrief] = useState<PageBrief | null>(null);
  const [logs, setLogs] = useState<AILog[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeLogIdx, setActiveLogIdx] = useState(0);
  const [generateLocale, setGenerateLocale] = useState("en");

  const LOCALE_OPTIONS = [
    { value: "en", label: "English" },
    { value: "zh-tw", label: "繁體中文" },
    { value: "zh-cn", label: "简体中文" },
    { value: "ja", label: "日本語" },
    { value: "ko", label: "한국어" },
    { value: "de", label: "Deutsch" },
  ];

  const PAGE_TYPE_LABELS: Record<string, string> = {
    product: "商品",
    application: "應用場景",
    category: "商品分類",
    comparison: "比較",
    custom: "自訂",
  };

  const BUYER_STAGE_LABELS: Record<string, string> = {
    awareness: "初步了解",
    consideration: "評估比較",
    decision: "準備採購",
  };

  const TONE_LABELS: Record<string, string> = {
    professional: "專業",
    technical: "技術",
    friendly: "友善",
  };

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [briefRes, logsRes] = await Promise.all([
        briefsApi.get(token, id),
        apiClient.get<AILog[]>(`/content/generate/logs/${id}`, token),
      ]);
      setBrief(briefRes.data);
      setLogs(logsRes);
      setActiveLogIdx(0);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "載入失敗");
    } finally {
      setLoading(false);
    }
  }, [id, token]);

  useEffect(() => { loadData(); }, [loadData]);

  const handleGenerate = async () => {
    if (!confirm("AI 產生內容將消耗 API 額度，確認繼續？")) return;
    setGenerating(true);
    try {
      await apiClient.post(`/content/generate`, { brief_id: id, target_locale: generateLocale }, token);
      await loadData();
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : "生成失敗");
    } finally {
      setGenerating(false);
    }
  };

  if (loading) return <p className="text-sm text-muted-foreground p-6">載入中…</p>;
  if (error) return <p className="text-sm text-red-500 p-6">{error}</p>;
  if (!brief) return null;

  const activeLog = logs[activeLogIdx] ?? null;
  const output = activeLog?.output_json as Record<string, unknown> | null;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Link href="/dashboard/briefs" className="text-xs text-muted-foreground hover:underline">← 返回寫作大綱</Link>
          </div>
          <h1 className="text-2xl font-semibold text-foreground">
            AI 預覽：{brief.title_draft ?? PAGE_TYPE_LABELS[brief.target_page_type] ?? brief.target_page_type}
          </h1>
          <div className="mt-1 flex items-center gap-3 text-sm text-muted-foreground">
            <span>頁型：<strong>{PAGE_TYPE_LABELS[brief.target_page_type] ?? brief.target_page_type}</strong></span>
            <StatusBadge
              status={(brief as unknown as Record<string, string>).ai_status ?? "pending"}
              labelMap={{ pending: "待生成", processing: "生成中", done: "完成", error: "錯誤" }}
            />
          </div>
        </div>
        <div className="flex gap-3">
          <Link
            href={`/dashboard/briefs/${id}/edit`}
            className="rounded-md border border-input px-4 py-2 text-sm font-medium text-foreground hover:bg-muted/50 transition-colors"
          >
            編輯大綱
          </Link>
          <button
            type="button"
            onClick={handleGenerate}
            disabled={generating}
            className="rounded-md bg-purple-700 px-4 py-2 text-sm font-medium text-white hover:bg-purple-800 transition-colors disabled:opacity-50"
          >
            {generating ? "產生中…" : "AI 重新產生"}
          </button>
          <select
            value={generateLocale}
            onChange={(e) => setGenerateLocale(e.target.value)}
            className="rounded border border-input px-3 py-2 text-sm text-foreground bg-white"
            title="選擇目標語言"
          >
            {LOCALE_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Brief info */}
      <div className="rounded-xl border border-gray-100 bg-muted/50 p-5 grid grid-cols-2 gap-x-8 gap-y-2 text-sm">
        {[
          ["受眾", brief.audience_persona],
          ["買家關注程度", BUYER_STAGE_LABELS[brief.buyer_stage] ?? brief.buyer_stage],
          ["主要關鍵字", brief.primary_keyword],
          ["次要關鍵字", brief.secondary_keywords],
          ["文字風格", TONE_LABELS[brief.tone] ?? brief.tone],
          ["目標字數", brief.word_count_target],
        ].map(([label, val]) => val ? (
          <div key={String(label)}>
            <span className="text-muted-foreground">{label}：</span>
            <span className="text-foreground">{String(val)}</span>
          </div>
        ) : null)}
        {brief.notes && (
          <div className="col-span-2">
            <span className="text-muted-foreground">備註：</span>
            <span className="text-foreground whitespace-pre-line">{brief.notes}</span>
          </div>
        )}
      </div>

      {/* Generation logs selector */}
      {logs.length === 0 ? (
        <div className="rounded-xl border-2 border-dashed border-gray-200 py-16 text-center text-muted-foreground">
          <p className="text-lg">尚無 AI 生成記錄</p>
          <p className="text-sm mt-1">點擊「AI 重新產生」開始產生內容</p>
        </div>
      ) : (
        <>
          {/* Log tabs */}
          {logs.length > 1 && (
            <div className="flex flex-wrap gap-2">
              {logs.map((log, idx) => (
                <button
                  key={log.id}
                  type="button"
                  onClick={() => setActiveLogIdx(idx)}
                  className={`rounded-md px-3 py-1 text-xs font-medium ${
                    idx === activeLogIdx
                      ? "bg-purple-700 text-white"
                      : "bg-muted text-muted-foreground hover:bg-muted"
                  }`}
                >
                  #{logs.length - idx} — {new Date(log.created_at).toLocaleString("zh-TW")}
                  {" "}<StatusBadge status={log.status} />
                </button>
              ))}
            </div>
          )}

          {/* Active log content */}
          {activeLog?.status === "error" ? (
            <div className="rounded-xl bg-red-50 border border-red-200 p-5 text-sm text-red-700">
              <p className="font-semibold mb-1">生成失敗</p>
              <p className="whitespace-pre-line">{activeLog.error_message}</p>
            </div>
          ) : output ? (
            <div className="space-y-4">
              <div className="flex items-center gap-3 text-xs text-muted-foreground">
                <span>模型：{activeLog?.model_name}</span>
                <span>時間：{new Date(activeLog?.created_at ?? "").toLocaleString("zh-TW")}</span>
              </div>

              {/* SEO */}
              {!!(output.seo_title || output.seo_description) && (
                <div className="rounded-xl border border-blue-100 bg-blue-50 p-5">
                  <h2 className="text-sm font-semibold text-blue-700 mb-2">搜尋標題設定</h2>
                  {!!output.seo_title && (
                    <p className="text-base font-medium text-foreground">{String(output.seo_title)}</p>
                  )}
                  {!!output.seo_description && (
                    <p className="mt-1 text-sm text-muted-foreground">{String(output.seo_description)}</p>
                  )}
                </div>
              )}

              {/* All other fields */}
              {Object.entries(output)
                .filter(([k]) => !["seo_title", "seo_description"].includes(k))
                .map(([key, value]) => (
                  <div key={key} className="rounded-xl border border-gray-200 bg-white p-5">
                    <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide mb-3">
                      {key.replace(/_/g, " ")}
                    </h2>
                    {Array.isArray(value) ? (
                      <ul className="space-y-2">
                        {(value as unknown[]).map((item, i) => (
                          <li key={i} className="text-sm text-foreground border-b border-gray-50 pb-2">
                            {typeof item === "object" ? (
                              <div className="space-y-1">
                                {Object.entries(item as Record<string, unknown>).map(([k2, v2]) => (
                                  <p key={k2}>
                                    <span className="font-medium text-muted-foreground">{k2}：</span>
                                    {String(v2)}
                                  </p>
                                ))}
                              </div>
                            ) : String(item)}
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-sm text-foreground whitespace-pre-line leading-relaxed">
                        {String(value)}
                      </p>
                    )}
                  </div>
                ))}
            </div>
          ) : null}
        </>
      )}
    </div>
  );
}
