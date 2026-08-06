"use client";
import { useEffect, useState, useCallback } from "react";
import { useAuth } from "@/lib/auth/store";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { FileText, Image as ImageIcon, File, RefreshCw, ExternalLink, Upload, Trash2, Loader2 } from "lucide-react";
import { assetsApi, type ContentAsset } from "@/lib/api/content";

type Meta = { total: number; page: number; page_size: number; total_pages: number };

function AssetIcon({ type }: { type: string }) {
  if (type === "pdf") return <FileText className="h-5 w-5 text-red-500" />;
  if (type === "image") return <ImageIcon className="h-5 w-5 text-blue-500" />;
  return <File className="h-5 w-5 text-muted-foreground" />;
}

function fmtSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

export default function AssetsPage() {
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";

  const [items, setItems] = useState<ContentAsset[]>([]);
  const [meta, setMeta] = useState<Meta | null>(null);
  const [typeFilter, setTypeFilter] = useState("");
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const PAGE_SIZE = 20;

  const load = useCallback(async (pageNum = page, filter = typeFilter) => {
    if (!token) return;
    setLoading(true); setError(null);
    try {
      const params: Record<string, string | number> = { page: pageNum, page_size: PAGE_SIZE };
      if (filter) params.asset_type = filter;
      const res = await assetsApi.list(token, params);
      setItems(res.data ?? []);
      setMeta(res.meta ?? null);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "載入失敗");
    } finally {
      setLoading(false);
    }
  }, [token, page, typeFilter]);

  useEffect(() => { void load(); }, [load]);

  const handleUpload = async (file: File) => {
    setUploading(true); setError(null);
    try {
      const fd = new FormData();
      fd.append("file", file);
      await assetsApi.upload(token, fd);
      setPage(1);
      await load(1, typeFilter);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "上傳失敗");
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("確定刪除此檔案？")) return;
    try {
      await assetsApi.delete(token, id);
      await load(page, typeFilter);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "刪除失敗");
    }
  };

  const SELECT_CLS = "rounded-md border border-input bg-background px-3 py-1.5 text-sm shadow-sm";
  const totalPages = meta?.total_pages ?? 1;

  return (
    <div>
      <div className="mb-6 flex items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">圖片與檔案</h1>
          <p className="mt-0.5 text-sm text-muted-foreground">上傳產品圖、PDF 規格書；也可在商品編輯頁直接上傳主圖</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => void load()} disabled={loading}>
            <RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />重新整理
          </Button>
          <label
            className={`inline-flex h-9 cursor-pointer items-center rounded-md bg-primary px-3 text-sm text-primary-foreground shadow hover:bg-primary/90 ${uploading ? "pointer-events-none opacity-50" : ""}`}
          >
            {uploading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Upload className="mr-2 h-4 w-4" />}
            {uploading ? "上傳中…" : "上傳檔案"}
            <input
              type="file"
              accept="image/jpeg,image/png,image/webp,image/gif,application/pdf"
              className="hidden"
              disabled={uploading}
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) void handleUpload(file);
                e.target.value = "";
              }}
            />
          </label>
        </div>
      </div>

      <div className="mb-4 flex gap-3">
        <select
          value={typeFilter}
          onChange={(e) => { setTypeFilter(e.target.value); setPage(1); }}
          className={SELECT_CLS}
        >
          <option value="">全部類型</option>
          <option value="image">圖片</option>
          <option value="pdf">PDF</option>
          <option value="other">其他</option>
        </select>
        {meta && <span className="self-center text-sm text-muted-foreground">共 {meta.total} 筆檔案</span>}
      </div>

      {error && <Alert variant="destructive" className="mb-4"><AlertDescription>{error}</AlertDescription></Alert>}

      {items.length === 0 && !loading ? (
        <div className="rounded-lg border-2 border-dashed border-muted p-12 text-center text-muted-foreground">
          <File className="mx-auto mb-3 h-10 w-10 opacity-40" />
          <p className="font-medium">尚無檔案</p>
          <p className="mt-1 text-sm">點右上角「上傳檔案」，或到商品編輯頁上傳主圖</p>
        </div>
      ) : (
        <div className="rounded-lg border">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-muted/40 text-left text-muted-foreground">
                <th className="px-4 py-2 font-medium">檔案</th>
                <th className="px-4 py-2 font-medium">類型</th>
                <th className="px-4 py-2 font-medium">大小</th>
                <th className="px-4 py-2 font-medium">網址</th>
                <th className="px-4 py-2 font-medium w-24">操作</th>
              </tr>
            </thead>
            <tbody>
              {items.map((a) => (
                <tr key={a.id} className="border-b last:border-0">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <AssetIcon type={a.asset_type} />
                      <span className="font-medium">{a.original_filename}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3"><Badge variant="secondary">{a.asset_type}</Badge></td>
                  <td className="px-4 py-3 text-muted-foreground">{fmtSize(a.file_size_bytes)}</td>
                  <td className="px-4 py-3">
                    <a href={a.public_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-primary hover:underline">
                      開啟 <ExternalLink className="h-3 w-3" />
                    </a>
                  </td>
                  <td className="px-4 py-3">
                    <Button variant="ghost" size="sm" className="text-destructive" onClick={() => void handleDelete(a.id)}>
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {totalPages > 1 && (
        <div className="mt-4 flex items-center justify-end gap-2">
          <Button
            variant="outline"
            size="sm"
            disabled={page <= 1 || loading}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
          >
            上一頁
          </Button>
          <span className="text-sm text-muted-foreground">{page} / {totalPages}</span>
          <Button
            variant="outline"
            size="sm"
            disabled={page >= totalPages || loading}
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
          >
            下一頁
          </Button>
        </div>
      )}
    </div>
  );
}
