"use client";

import { useCallback, useEffect, useState } from "react";
import { CheckCircle2, RefreshCw, ShieldAlert, XCircle } from "lucide-react";
import { useAuth } from "@/lib/auth/store";
import { apiClient } from "@/lib/api/client";

type TrustCheckItem = {
  key: string;
  label: string;
  passed: boolean;
  hint: string;
};

type TrustCheckResult = {
  applicable: boolean;
  page_type: string;
  score: number | null;
  passed?: number;
  total?: number;
  checklist: TrustCheckItem[];
  message?: string;
};

export function TrustCheckCard({ pageId }: { pageId: string }) {
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";
  const [result, setResult] = useState<TrustCheckResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.get<{ data: TrustCheckResult }>(
        `/content/pages/${pageId}/trust-check`,
        token,
      );
      setResult(res.data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "載入失敗");
    } finally {
      setLoading(false);
    }
  }, [pageId, token]);

  useEffect(() => {
    void load();
  }, [load]);

  if (loading) {
    return <p className="text-sm text-muted-foreground">信任內容檢核載入中…</p>;
  }
  if (error) {
    return <p className="text-sm text-red-500">信任內容檢核失敗：{error}</p>;
  }
  if (!result || !result.applicable) {
    return null;
  }

  return (
    <div className="mt-6 rounded-lg border bg-card p-4">
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <ShieldAlert className="h-4 w-4 text-muted-foreground" />
          <h2 className="text-base font-semibold">信任內容檢核</h2>
          <span
            className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${
              (result.score ?? 0) >= 80
                ? "bg-green-100 text-green-800"
                : (result.score ?? 0) >= 50
                  ? "bg-yellow-100 text-yellow-800"
                  : "bg-red-100 text-red-700"
            }`}
          >
            {result.score} 分（{result.passed}/{result.total}）
          </span>
        </div>
        <button
          type="button"
          onClick={() => void load()}
          className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
        >
          <RefreshCw className="h-3 w-3" />
          重新檢核
        </button>
      </div>
      <ul className="space-y-2">
        {result.checklist.map((item) => (
          <li key={item.key} className="flex items-start gap-2 text-sm">
            {item.passed ? (
              <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-green-600" />
            ) : (
              <XCircle className="mt-0.5 h-4 w-4 shrink-0 text-red-500" />
            )}
            <div>
              <span className={item.passed ? "" : "font-medium"}>{item.label}</span>
              {!item.passed && (
                <p className="text-xs text-muted-foreground">{item.hint}</p>
              )}
            </div>
          </li>
        ))}
      </ul>
      <p className="mt-3 text-xs text-muted-foreground">
        儲存內容後按「重新檢核」更新結果；此標準也提供 ContentFlow 產生信任類內容 brief 時參考。
      </p>
    </div>
  );
}
