"use client";
/**
 * RelationsPanel — reusable panel for managing M2M links on a Product or Application.
 *
 * Props:
 *   entityType: "product" | "application"
 *   entityId:   UUID string
 *   linkType:   "applications" | "certifications" | "faqs" (for product)
 *               "faqs" (for application)
 */
import { useEffect, useState, useCallback } from "react";
import { useAuth } from "@/lib/auth/store";
import { relationsApi, applicationsApi, certificationsApi, faqsApi } from "@/lib/api/content";

type LinkedItem = { id: string; name: string; slug: string };
type AvailableItem = { id: string; label: string };

type Props = {
  entityType: "product" | "application";
  entityId: string;
  linkType: "applications" | "certifications" | "faqs";
  title?: string;
};

export function RelationsPanel({ entityType, entityId, linkType, title }: Props) {
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";

  const [linked, setLinked] = useState<LinkedItem[]>([]);
  const [available, setAvailable] = useState<AvailableItem[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [linking, setLinking] = useState(false);
  const [unlinking, setUnlinking] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const loadLinked = useCallback(async () => {
    try {
      let items: LinkedItem[] = [];
      if (entityType === "product") {
        if (linkType === "applications") items = await relationsApi.listProductApplications(token, entityId);
        else if (linkType === "certifications") items = await relationsApi.listProductCertifications(token, entityId);
        else if (linkType === "faqs") items = await relationsApi.listProductFAQs(token, entityId);
      } else {
        if (linkType === "faqs") items = await relationsApi.listApplicationFAQs(token, entityId);
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
    loadLinked();
    loadAvailable();
  }, [loadLinked, loadAvailable]);

  const handleLink = async () => {
    if (!selectedId) return;
    setLinking(true);
    try {
      if (entityType === "product") {
        if (linkType === "applications") await relationsApi.linkProductApplication(token, entityId, selectedId);
        else if (linkType === "certifications") await relationsApi.linkProductCertification(token, entityId, selectedId);
        else if (linkType === "faqs") await relationsApi.linkProductFAQ(token, entityId, selectedId);
      } else {
        if (linkType === "faqs") await relationsApi.linkApplicationFAQ(token, entityId, selectedId);
      }
      setSelectedId("");
      await loadLinked();
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : "關聯失敗");
    } finally {
      setLinking(false);
    }
  };

  const handleUnlink = async (targetId: string) => {
    setUnlinking(targetId);
    try {
      if (entityType === "product") {
        if (linkType === "applications") await relationsApi.unlinkProductApplication(token, entityId, targetId);
        else if (linkType === "certifications") await relationsApi.unlinkProductCertification(token, entityId, targetId);
        else if (linkType === "faqs") await relationsApi.unlinkProductFAQ(token, entityId, targetId);
      } else {
        if (linkType === "faqs") await relationsApi.unlinkApplicationFAQ(token, entityId, targetId);
      }
      await loadLinked();
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : "移除失敗");
    } finally {
      setUnlinking(null);
    }
  };

  // Filter out already-linked items from available list
  const linkedIds = new Set(linked.map((l) => l.id));
  const unlinked = available.filter((a) => !linkedIds.has(a.id));

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5">
      <h3 className="text-sm font-semibold text-gray-700 mb-3">
        {title ?? `關聯 ${linkType}`}
        <span className="ml-2 text-xs text-gray-400 font-normal">({linked.length} 筆)</span>
      </h3>

      {loading ? (
        <p className="text-xs text-gray-400">載入中…</p>
      ) : (
        <>
          {/* Linked items */}
          {linked.length > 0 ? (
            <ul className="mb-3 divide-y divide-gray-50">
              {linked.map((item) => (
                <li key={item.id} className="flex items-center justify-between py-1.5 text-sm">
                  <span className="text-gray-700 truncate max-w-xs">{item.name}</span>
                  <button
                    type="button"
                    onClick={() => handleUnlink(item.id)}
                    disabled={unlinking === item.id}
                    className="ml-3 text-xs text-red-500 hover:text-red-700 disabled:opacity-50 whitespace-nowrap"
                  >
                    {unlinking === item.id ? "移除中…" : "× 移除"}
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-xs text-gray-400 mb-3">尚無關聯</p>
          )}

          {/* Add new link */}
          {unlinked.length > 0 && (
            <div className="flex gap-2 mt-2">
              <select
                value={selectedId}
                onChange={(e) => setSelectedId(e.target.value)}
                className="flex-1 min-w-0 rounded-md border border-gray-300 px-2 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">— 選擇要關聯的項目 —</option>
                {unlinked.map((a) => (
                  <option key={a.id} value={a.id}>{a.label}</option>
                ))}
              </select>
              <button
                type="button"
                onClick={handleLink}
                disabled={!selectedId || linking}
                className="rounded-md bg-blue-700 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-800 disabled:opacity-50 whitespace-nowrap"
              >
                {linking ? "關聯中…" : "+ 新增"}
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
