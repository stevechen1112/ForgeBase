"use client";

import { useCallback, useEffect, useState } from "react";
import { Plus, RefreshCw, Save, Trash2 } from "lucide-react";
import { useAuth } from "@/lib/auth/store";
import { glossaryApi, type GlossaryEntry } from "@/lib/api/content";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

export function GlossaryCard() {
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";

  const [entries, setEntries] = useState<GlossaryEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const data = await glossaryApi.list(token);
      setEntries(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "載入術語表失敗");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    void load();
  }, [load]);

  const updateEntry = (index: number, patch: Partial<GlossaryEntry>) => {
    setEntries((prev) => prev.map((e, i) => (i === index ? { ...e, ...patch } : e)));
  };

  async function handleSave() {
    const cleaned = entries
      .map((e) => ({ source: e.source.trim(), target: e.target.trim(), note: e.note?.trim() || undefined }))
      .filter((e) => e.source && e.target);
    if (cleaned.length !== entries.length) {
      setError("有空白列（來源或譯名為空），請補齊或刪除後再儲存。");
      return;
    }
    setSaving(true);
    setError(null);
    setSuccess(null);
    try {
      const data = await glossaryApi.update(token, cleaned);
      setEntries(data);
      setSuccess(`術語表已更新（${data.length} 條），AI 起草翻譯時即刻生效。`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "儲存術語表失敗");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <CardTitle>翻譯術語表（AI 起草）</CardTitle>
            <CardDescription>
              固定 B2B 術語譯名，AI 起草另一語系內容時會強制採用。例如 Chrome Vanadium → 鉻釩鋼。
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={() => void load()} disabled={loading || saving}>
              <RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />重新整理
            </Button>
            <Button size="sm" onClick={() => void handleSave()} disabled={loading || saving || !token}>
              <Save className={`mr-2 h-4 w-4 ${saving ? "animate-pulse" : ""}`} />儲存術語表
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {error ? (
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        ) : null}
        {success ? (
          <Alert>
            <AlertDescription>{success}</AlertDescription>
          </Alert>
        ) : null}

        {loading ? (
          <p className="text-sm text-muted-foreground">載入中…</p>
        ) : (
          <>
            {entries.length === 0 && (
              <p className="rounded-md border border-dashed px-3 py-4 text-center text-sm text-muted-foreground">
                尚無術語。新增常用材料、製程、認證的固定譯名，翻譯品質會明顯更穩定。
              </p>
            )}
            {entries.map((entry, i) => (
              <div key={i} className="grid grid-cols-[1fr_1fr_1fr_auto] items-center gap-2">
                <Input
                  value={entry.source}
                  onChange={(e) => updateEntry(i, { source: e.target.value })}
                  placeholder="原文（例：Chrome Vanadium）"
                  maxLength={120}
                />
                <Input
                  value={entry.target}
                  onChange={(e) => updateEntry(i, { target: e.target.value })}
                  placeholder="固定譯名（例：鉻釩鋼）"
                  maxLength={120}
                />
                <Input
                  value={entry.note ?? ""}
                  onChange={(e) => updateEntry(i, { note: e.target.value })}
                  placeholder="備註（可選）"
                  maxLength={200}
                />
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => setEntries((prev) => prev.filter((_, j) => j !== i))}
                  aria-label="刪除此術語"
                >
                  <Trash2 className="h-4 w-4 text-muted-foreground" />
                </Button>
              </div>
            ))}
            <Button
              variant="outline"
              size="sm"
              onClick={() => setEntries((prev) => [...prev, { source: "", target: "" }])}
            >
              <Plus className="mr-2 h-4 w-4" />新增術語
            </Button>
          </>
        )}
      </CardContent>
    </Card>
  );
}
