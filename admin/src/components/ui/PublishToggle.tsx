"use client";
import { useState } from "react";
import { useAuth } from "@/lib/auth/store";
import { publishApi } from "@/lib/api/content";

type Props = {
  /** API entity name, e.g. "products", "applications", "categories" */
  entity: string;
  id: string;
  currentStatus: string;
  onStatusChange?: (newStatus: string) => void;
};

export function PublishToggle({ entity, id, currentStatus, onStatusChange }: Props) {
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";
  const [loading, setLoading] = useState(false);

  const isPublished = currentStatus === "published";

  const handleClick = async () => {
    setLoading(true);
    try {
      if (isPublished) {
        await publishApi.unpublish(token, entity, id);
        onStatusChange?.("draft");
      } else {
        await publishApi.publish(token, entity, id);
        onStatusChange?.("published");
      }
    } catch {
      alert("操作失敗，請重試");
    } finally {
      setLoading(false);
    }
  };

  return (
    <button
      type="button"
      onClick={handleClick}
      disabled={loading}
      className={`rounded px-2 py-1 text-xs font-medium transition-colors disabled:opacity-50 ${
        isPublished
          ? "bg-amber-50 text-amber-700 hover:bg-amber-100"
          : "bg-green-50 text-green-700 hover:bg-green-100"
      }`}
    >
      {loading ? "..." : isPublished ? "下架" : "發布"}
    </button>
  );
}
