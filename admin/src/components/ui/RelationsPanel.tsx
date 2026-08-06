"use client";
/**
 * RelationsPanel — manage M2M links on a Product or Application.
 */
import { useEffect, useState, useCallback } from "react";
import { useAuth } from "@/lib/auth/store";
import { relationsApi, applicationsApi, certificationsApi, faqsApi } from "@/lib/api/content";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

type LinkedItem = { id: string; name: string; slug: string };
type AvailableItem = { id: string; label: string };

type Props = {
  entityType: "product" | "application";
  entityId: string;
  linkType: "applications" | "certifications" | "faqs";
  title?: string;
};

const SELECT_CLS =
  "flex h-9 flex-1 min-w-0 rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring";

export function RelationsPanel({ entityType, entityId, linkType, title }: Props) {
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";

  const [linked, setLinked] = useState<LinkedItem[]>([]);
  const [available, setAvailable] = useState<AvailableItem[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [linking, setLinking] = useState(false);
  const [unlinking, setUnlinking] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadLinked = useCallback(async () => {
    try {
      let items: LinkedItem[] = [];
      if (entityType === "product") {
        if (linkType === "applications") items = await relationsApi.listProductApplications(token, entityId);
        else if (linkType === "certifications") items = await relationsApi.listProductCertifications(token, entityId);
        else if (linkType === "faqs") items = await relationsApi.listProductFAQs(token, entityId);
      } else if (linkType === "faqs") {
        items = await relationsApi.listApplicationFAQs(token, entityId);
      }
      setLinked(items);
    } finally {
      setLoading(false);
    }
  }, [token, entityId, entityType, linkType]);

  const loadAvailable = useCallback(async () => {
    try {
      if (linkType === "applications") {
        const res = await applicationsApi.list(token, { page_size: 200 });
        setAvailable(res.data.map((a) => ({ id: a.id, label: a.application_name })));
      } else if (linkType === "certifications") {
        const res = await certificationsApi.list(token, { page_size: 200 });
        setAvailable(res.data.map((c) => ({ id: c.id, label: c.cert_name })));
      } else if (linkType === "faqs") {
        const res = await faqsApi.list(token, { page_size: 500 });
        setAvailable(res.data.map((f) => ({ id: f.id, label: f.question.substring(0, 80) })));
      }
    } catch { /* ignore */ }
  }, [token, linkType]);

  useEffect(() => {
    void loadLinked();
    void loadAvailable();
  }, [loadLinked, loadAvailable]);

  const handleLink = async () => {
    if (!selectedId) return;
    setLinking(true); setError(null);
    try {
      if (entityType === "product") {
        if (linkType === "applications") await relationsApi.linkProductApplication(token, entityId, selectedId);
        else if (linkType === "certifications") await relationsApi.linkProductCertification(token, entityId, selectedId);
        else if (linkType === "faqs") await relationsApi.linkProductFAQ(token, entityId, selectedId);
      } else if (linkType === "faqs") {
        await relationsApi.linkApplicationFAQ(token, entityId, selectedId);
      }
      setSelectedId("");
      await loadLinked();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "關聯失敗");
    } finally {
      setLinking(false);
    }
  };

  const handleUnlink = async (targetId: string) => {
    setUnlinking(targetId); setError(null);
    try {
      if (entityType === "product") {
        if (linkType === "applications") await relationsApi.unlinkProductApplication(token, entityId, targetId);
        else if (linkType === "certifications") await relationsApi.unlinkProductCertification(token, entityId, targetId);
        else if (linkType === "faqs") await relationsApi.unlinkProductFAQ(token, entityId, targetId);
      } else if (linkType === "faqs") {
        await relationsApi.unlinkApplicationFAQ(token, entityId, targetId);
      }
      await loadLinked();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "移除失敗");
    } finally {
      setUnlinking(null);
    }
  };

  const linkedIds = new Set(linked.map((l) => l.id));
  const unlinked = available.filter((a) => !linkedIds.has(a.id));

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base">
          {title ?? `關聯 ${linkType}`}
          <span className="ml-2 text-xs font-normal text-muted-foreground">({linked.length} 筆)</span>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {error && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}

        {loading ? (
          <p className="text-xs text-muted-foreground">載入中…</p>
        ) : (
          <>
            {linked.length > 0 ? (
              <ul className="divide-y rounded-md border">
                {linked.map((item) => (
                  <li key={item.id} className="flex items-center justify-between px-3 py-2 text-sm">
                    <span className="truncate max-w-xs">{item.name}</span>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      className="text-destructive"
                      onClick={() => void handleUnlink(item.id)}
                      disabled={unlinking === item.id}
                    >
                      {unlinking === item.id ? "移除中…" : "移除"}
                    </Button>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-xs text-muted-foreground">尚無關聯</p>
            )}

            {unlinked.length > 0 && (
              <div className="flex gap-2">
                <select
                  value={selectedId}
                  onChange={(e) => setSelectedId(e.target.value)}
                  className={SELECT_CLS}
                >
                  <option value="">— 選擇要關聯的項目 —</option>
                  {unlinked.map((a) => (
                    <option key={a.id} value={a.id}>{a.label}</option>
                  ))}
                </select>
                <Button
                  type="button"
                  size="sm"
                  onClick={() => void handleLink()}
                  disabled={!selectedId || linking}
                >
                  {linking ? "關聯中…" : "新增"}
                </Button>
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}
