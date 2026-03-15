"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth/store";

type ApiResponse<T> = { data: T };
type EntityLoader<T> = (token: string, id: string) => Promise<ApiResponse<T>>;

export function useEntityEditorData<T>(id: string, loader: EntityLoader<T>) {
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    setLoading(true);
    setError(null);

    loader(token, id)
      .then((response) => {
        if (!active) return;
        setData(response.data);
      })
      .catch((err: unknown) => {
        if (!active) return;
        setError(err instanceof Error ? err.message : "載入失敗");
      })
      .finally(() => {
        if (!active) return;
        setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [id, loader, token]);

  return { data, error, loading, token };
}