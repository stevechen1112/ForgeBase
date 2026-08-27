"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { ExternalLink, RefreshCw, TriangleAlert } from "lucide-react";
import { Button } from "@/components/ui/button";
import { usePlatformAuth } from "@/lib/auth/platform-store";
import {
  platformAdminApi,
  type DeliveryBoardItem,
  type DeliveryStage,
} from "@/lib/api/platform-admin";

const STAGES: { value: DeliveryStage; label: string }[] = [
  { value: "intake", label: "需求確認" },
  { value: "content", label: "收集內容" },
  { value: "build", label: "製作網站" },
  { value: "qa", label: "測試驗收" },
  { value: "client_review", label: "客戶確認" },
  { value: "launch_ready", label: "準備上線" },
  { value: "live", label: "已上線" },
  { value: "on_hold", label: "暫緩" },
];

const STAGE_LABEL = Object.fromEntries(
  STAGES.map((stage) => [stage.value, stage.label]),
);

export default function DeliveryBoardPage() {
  const { state } = usePlatformAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";
  const [items, setItems] = useState<DeliveryBoardItem[]>([]);
  const [stage, setStage] = useState<"" | DeliveryStage>("");
  const [includeLive, setIncludeLive] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError("");
    try {
      setItems(
        await platformAdminApi.deliveryBoard(token, {
          stage: stage || undefined,
          include_live: includeLive,
        }),
      );
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "無法讀取交付工作台。");
    } finally {
      setLoading(false);
    }
  }, [token, stage, includeLive]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">網站交付</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            從選範本、內容確認到驗收與上線，技術發布狀態與交付進度分開管理。
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
        <select
          value={stage}
          onChange={(event) => {
            const nextStage = event.target.value as "" | DeliveryStage;
            setStage(nextStage);
            if (nextStage === "live") setIncludeLive(true);
          }}
          className="h-10 rounded-md border bg-background px-3 text-sm"
        >
          <option value="">全部交付階段</option>
          {STAGES.map((item) => (
            <option key={item.value} value={item.value}>
              {item.label}
            </option>
          ))}
        </select>
        <label className="flex h-10 items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={includeLive}
            onChange={(event) => {
              setIncludeLive(event.target.checked);
              if (!event.target.checked && stage === "live") setStage("");
            }}
          />
          包含已上線網站
        </label>
      </div>
      <div className="overflow-hidden rounded-xl border bg-card shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[900px] text-sm">
            <thead>
              <tr className="border-b bg-muted/40 text-left text-xs text-muted-foreground">
                <th className="px-4 py-3">客戶網站</th>
                <th className="px-4 py-3">交付階段</th>
                <th className="px-4 py-3">技術檢查</th>
                <th className="px-4 py-3">目標上線</th>
                <th className="px-4 py-3">負責人</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr
                  key={item.id}
                  className="border-b last:border-0 hover:bg-muted/30"
                >
                  <td className="px-4 py-3">
                    <p className="font-medium">{item.tenant_name}</p>
                    <p className="text-xs text-muted-foreground">
                      {item.template_key} ·{" "}
                      {item.primary_domain || "尚未設定網域"}
                    </p>
                  </td>
                  <td className="px-4 py-3">
                    <p>{STAGE_LABEL[item.delivery_stage]}</p>
                    <p className="text-xs text-muted-foreground">
                      驗收：
                      {item.acceptance_status === "accepted"
                        ? "已確認"
                        : item.acceptance_status === "requested"
                          ? "等待客戶確認"
                          : "尚未確認"}
                    </p>
                  </td>
                  <td className="px-4 py-3">
                    {item.technical_status === "blocked" || item.last_error ? (
                      <span className="inline-flex items-center gap-1 text-red-700">
                        <TriangleAlert className="h-3.5 w-3.5" />
                        {item.last_error || "需處理"}
                      </span>
                    ) : (
                      <span className="text-emerald-700">
                        {item.cms_connected ? "CMS 已串接" : "等待 CMS 串接"}
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">
                    {item.target_launch_at
                      ? new Date(item.target_launch_at).toLocaleDateString(
                          "zh-TW",
                        )
                      : "未設定"}
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">
                    {item.delivery_owner_name || "未指派"}
                  </td>
                  <td className="px-4 py-3">
                    <Link
                      href={`/platform/tenants/${item.tenant_id}`}
                      className="inline-flex items-center gap-1 text-primary hover:underline"
                    >
                      開啟交付單
                      <ExternalLink className="h-3.5 w-3.5" />
                    </Link>
                  </td>
                </tr>
              ))}
              {!loading && !items.length && (
                <tr>
                  <td
                    colSpan={6}
                    className="px-4 py-12 text-center text-muted-foreground"
                  >
                    沒有符合條件的網站交付單。
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
