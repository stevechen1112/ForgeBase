"use client";
import { useEffect, useState, useCallback } from "react";
import { useAuth } from "@/lib/auth/store";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { RefreshCw, Brain, PlayCircle, CheckCircle2, XCircle } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

type MLStatus = {
  model_type?: string;
  trained?: boolean;
  message?: string;
  accuracy?: number;
  training_samples?: number;
  last_trained_at?: string;
  feature_importance?: Record<string, number>;
};

type TrainResult = {
  success?: boolean;
  message?: string;
  accuracy?: number;
  training_samples?: number;
};

export default function MLScoringPage() {
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";
  const [status, setStatus] = useState<MLStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [training, setTraining] = useState(false);
  const [trainResult, setTrainResult] = useState<TrainResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadStatus = useCallback(() => {
    setLoading(true); setError(null);
    fetch(`${API_BASE}/tracking/ml/status`, { headers: { Authorization: `Bearer ${token}` } })
      .then(r => r.json()).then(setStatus).catch(e => setError(e.message)).finally(() => setLoading(false));
  }, [token]);

  useEffect(() => { loadStatus(); }, [loadStatus]);

  const trainModel = async () => {
    setTraining(true); setTrainResult(null); setError(null);
    try {
      const r = await fetch(`${API_BASE}/tracking/ml/train`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail ?? "訓練失敗");
      setTrainResult(d);
      loadStatus();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally { setTraining(false); }
  };

  const featureEntries = status?.feature_importance
    ? Object.entries(status.feature_importance).sort((a, b) => b[1] - a[1])
    : [];

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">ML 意圖評分</h1>
          <p className="mt-0.5 text-sm text-muted-foreground">機器學習模型訓練與意圖預測狀態</p>
        </div>
        <Button variant="outline" size="sm" onClick={loadStatus} disabled={loading}>
          <RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />重新整理
        </Button>
      </div>

      {error && (
        <Alert variant="destructive" className="mb-4">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {trainResult && (
        <Alert className="mb-4 border-green-200 bg-green-50 text-green-800">
          <CheckCircle2 className="h-4 w-4" />
          <AlertDescription>{trainResult.message ?? "訓練完成"}{trainResult.accuracy !== undefined && ` — 準確率：${(trainResult.accuracy * 100).toFixed(1)}%`}</AlertDescription>
        </Alert>
      )}

      {/* Model Status Card */}
      <Card className="mb-6">
        <CardContent className="pt-6">
          <div className="flex items-start gap-4">
            <Brain className={`h-12 w-12 ${status?.trained ? "text-primary" : "text-muted-foreground/40"}`} />
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <h2 className="text-lg font-semibold">{status?.model_type ?? "Intent Model"}</h2>
                {status?.trained
                  ? <Badge className="bg-green-100 text-green-700"><CheckCircle2 className="mr-1 h-3 w-3" />已訓練</Badge>
                  : <Badge className="bg-gray-100 text-gray-600"><XCircle className="mr-1 h-3 w-3" />未訓練</Badge>}
              </div>
              <p className="mt-1 text-sm text-muted-foreground">{status?.message ?? "—"}</p>
              {status?.last_trained_at && (
                <p className="mt-1 text-xs text-muted-foreground">
                  最後訓練：{new Date(status.last_trained_at).toLocaleString("zh-TW")}
                </p>
              )}
            </div>
            <Button onClick={trainModel} disabled={training} className="shrink-0">
              <PlayCircle className="mr-2 h-4 w-4" />
              {training ? "訓練中…" : "重新訓練"}
            </Button>
          </div>

          {status?.trained && (
            <div className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-3">
              {status.accuracy !== undefined && (
                <div className="rounded-lg bg-muted/50 p-3">
                  <p className="text-xs text-muted-foreground">模型準確率</p>
                  <p className="mt-1 text-xl font-bold">{(status.accuracy * 100).toFixed(1)}%</p>
                </div>
              )}
              {status.training_samples !== undefined && (
                <div className="rounded-lg bg-muted/50 p-3">
                  <p className="text-xs text-muted-foreground">訓練樣本數</p>
                  <p className="mt-1 text-xl font-bold">{status.training_samples.toLocaleString()}</p>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Feature Importance */}
      {featureEntries.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">特徵重要性</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {featureEntries.map(([feat, imp]) => (
              <div key={feat}>
                <div className="mb-1 flex justify-between text-sm">
                  <span className="font-medium">{feat}</span>
                  <span className="text-muted-foreground">{(imp * 100).toFixed(1)}%</span>
                </div>
                <div className="h-2 rounded-full bg-muted">
                  <div className="h-2 rounded-full bg-primary" style={{ width: `${imp * 100}%` }} />
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Training Info */}
      <Card className="mt-6">
        <CardHeader><CardTitle className="text-base">模型說明</CardTitle></CardHeader>
        <CardContent className="text-sm text-muted-foreground space-y-2">
          <p>ML 模型使用訪客行為歷史訓練，自動學習哪些行為序列最能預測最終 RFQ 轉換。</p>
          <ul className="list-inside list-disc space-y-1 pl-2">
            <li>訓練資料：過去所有訪客行為事件與轉換結果</li>
            <li>輸入特徵：page_views、product_views、pdf_downloads、session_count、days_since_first_visit 等</li>
            <li>輸出：0–100 意圖分數（補充規則型評分）</li>
            <li>建議在累積超過 200 筆 RFQ 後進行首次訓練以確保準確性</li>
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}
