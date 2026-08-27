"use client";

import { useCallback, useEffect, useState } from "react";
import { ArrowDown, ArrowUp, Loader2, Star, Trash2, Upload } from "lucide-react";
import { assetsApi, productGalleryApi, productsApi, type ContentAsset } from "@/lib/api/content";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";

type Props = {
  token: string;
  productId: string;
  mainImageUrl: string;
  onMainImageChange: (url: string) => void;
};

export function ProductGalleryEditor({ token, productId, mainImageUrl, onMainImageChange }: Props) {
  const [items, setItems] = useState<ContentAsset[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await assetsApi.list(token, { product_id: productId, asset_type: "image", page_size: 40 });
      setItems([...response.data].sort((a, b) => a.display_order - b.display_order || a.created_at.localeCompare(b.created_at)));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "無法載入圖庫");
    } finally {
      setLoading(false);
    }
  }, [productId, token]);

  useEffect(() => { void load(); }, [load]);

  const persistOrder = async (next: ContentAsset[]) => {
    setItems(next);
    await productGalleryApi.reorder(token, productId, next.map((item, index) => ({ id: item.id, display_order: index })));
  };

  const handleUpload = async (file: File) => {
    setBusy(true);
    setError(null);
    try {
      const form = new FormData();
      form.append("file", file);
      form.append("product_id", productId);
      await assetsApi.upload(token, form);
      await load();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "上傳失敗");
    } finally {
      setBusy(false);
    }
  };

  const handleDelete = async (asset: ContentAsset) => {
    if (!confirm("確定移除此圖？")) return;
    setBusy(true);
    try {
      await assetsApi.delete(token, asset.id);
      if (asset.public_url === mainImageUrl) {
        const remaining = items.filter((item) => item.id !== asset.id);
        const nextMain = remaining[0]?.public_url || "";
        onMainImageChange(nextMain);
        if (nextMain) await productsApi.update(token, productId, { image_url: nextMain });
      }
      await load();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "刪除失敗");
    } finally {
      setBusy(false);
    }
  };

  const handleSetMain = async (asset: ContentAsset) => {
    setBusy(true);
    try {
      onMainImageChange(asset.public_url);
      await productsApi.update(token, productId, { image_url: asset.public_url, image_alt: asset.alt_text || undefined });
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "無法設為主圖");
    } finally {
      setBusy(false);
    }
  };

  const move = async (index: number, direction: -1 | 1) => {
    const target = index + direction;
    if (target < 0 || target >= items.length) return;
    const next = [...items];
    [next[index], next[target]] = [next[target], next[index]];
    setBusy(true);
    try {
      await persistOrder(next);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "排序失敗");
      await load();
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between gap-3">
        <Label>商品圖庫</Label>
        <label className={`inline-flex h-8 cursor-pointer items-center gap-2 rounded-md border px-3 text-xs ${busy ? "pointer-events-none opacity-50" : ""}`}>
          {busy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Upload className="h-3.5 w-3.5" />}
          新增圖片
          <input
            type="file"
            accept="image/jpeg,image/png,image/webp,image/gif"
            className="hidden"
            disabled={busy}
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (file) void handleUpload(file);
              event.target.value = "";
            }}
          />
        </label>
      </div>
      <p className="text-xs text-muted-foreground">可上傳多張圖並排序。第一張不必等於主圖；按星號可把該圖設為列表與分享用主圖。</p>
      {error && <p className="text-sm text-destructive">{error}</p>}
      {loading ? (
        <p className="text-sm text-muted-foreground">載入圖庫中…</p>
      ) : items.length === 0 ? (
        <p className="rounded-md border bg-muted/20 px-3 py-4 text-sm text-muted-foreground">尚無圖庫圖片。上傳後會出現在商品詳情頁。</p>
      ) : (
        <ul className="grid gap-3 sm:grid-cols-2">
          {items.map((asset, index) => {
            const isMain = asset.public_url === mainImageUrl;
            return (
              <li key={asset.id} className="flex gap-3 rounded-lg border p-2">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={asset.public_url} alt={asset.alt_text || ""} className="h-20 w-20 rounded-md object-cover bg-muted" />
                <div className="min-w-0 flex-1 space-y-2">
                  <p className="truncate text-xs text-muted-foreground">{asset.original_filename}</p>
                  <div className="flex flex-wrap gap-1">
                    <Button type="button" size="icon" variant="ghost" disabled={index === 0 || busy} onClick={() => void move(index, -1)} aria-label="上移"><ArrowUp className="h-4 w-4" /></Button>
                    <Button type="button" size="icon" variant="ghost" disabled={index === items.length - 1 || busy} onClick={() => void move(index, 1)} aria-label="下移"><ArrowDown className="h-4 w-4" /></Button>
                    <Button type="button" size="icon" variant="ghost" disabled={busy || isMain} onClick={() => void handleSetMain(asset)} aria-label="設為主圖"><Star className={`h-4 w-4 ${isMain ? "fill-amber-400 text-amber-400" : ""}`} /></Button>
                    <Button type="button" size="icon" variant="ghost" className="text-destructive" disabled={busy} onClick={() => void handleDelete(asset)} aria-label="刪除"><Trash2 className="h-4 w-4" /></Button>
                  </div>
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
