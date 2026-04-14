"use client";
import { useEffect, useState, useCallback } from "react";
import { useAuth } from "@/lib/auth/store";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { FileText, Image as ImageIcon, File, RefreshCw, ExternalLink } from "lucide-react";
import { API_BASE, buildApiHeaders } from "@/lib/api/client";

type Asset = {
  id: string;
  original_filename: string;
  public_url: string;
  mime_type: string;
  file_size_bytes: number;
  asset_type: string;
  alt_text: string | null;
  title: string | null;
  is_indexable: boolean;
  product_id: string | null;
  page_id: string | null;
  uploaded_by: string;
  created_at: string;
};

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

  const [items, setItems] = useState<Asset[]>([]);
  const [meta, setMeta] = useState<Meta | null>(null);
  const [typeFilter, setTypeFilter] = useState("");
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const PAGE_SIZE = 20;

  const load = useCallback(() => {
    setLoading(true); setError(null);
    const params = new URLSearchParams({ page: String(page), page_size: String(PAGE_SIZE) });
    if (typeFilter) params.set("asset_type", typeFilter);
    fetch(`${API_BASE}/content/assets?${params}`, { headers: buildApiHeaders(token) })
      .then(r => r.json())
      .then(d => { setItems(d.data ?? []); setMeta(d.meta ?? null); })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, [token, page, typeFilter]);

  useEffect(() => { load(); }, [load]);

  const SELECT_CLS = "rounded-md border border-input bg-background px-3 py-1.5 text-sm shadow-sm";

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">媒體庫</h1>
          <p className="mt-0.5 text-sm text-muted-foreground">管理上傳的圖片、PDF 規格書與其他資產</p>
        </div>
        <Button variant="outline" size="sm" onClick={load} disabled={loading}>
          <RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />重新整理
        </Button>
      </div>

      {/* Filters */}
      <div className="mb-4 flex gap-3">
        <select value={typeFilter} onChange={e => { setTypeFilter(e.target.value); setPage(1); }} className={SELECT_CLS}>
          <option value="">全部類型</option>
          <option value="pdf">PDF</option>
          <option value="image">圖片</option>
          <option value="doc">文件</option>
        </select>
        {meta && <span className="self-center text-sm text-muted-foreground">共 {meta.total} 筆資產</span>}
      </div>

      {error && <Alert variant="destructive" className="mb-4"><AlertDescription>{error}</AlertDescription></Alert>}

      {items.length === 0 && !loading ? (
        <div className="rounded-lg border-2 border-dashed border-muted p-12 text-center text-muted-foreground">
          <File className="mx-auto mb-3 h-10 w-10 opacity-40" />
          <p className="font-medium">尚無資產</p>
          <p className="mt-1 text-sm">透過商品或頁面編輯介面上傳資產</p>
        </div>
      ) : (
        <div className="rounded-lg border">
          <table className="w-full text-sm">
            <thead className="bg-muted/50">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-muted-foreground">類型</th>
                <th className="px-4 py-3 text-left font-medium text-muted-foreground">檔名</th>
                <th className="px-4 py-3 text-left font-medium text-muted-foreground">大小</th>
                <th className="px-4 py-3 text-left font-medium text-muted-foreground">屬性</th>
                <th className="px-4 py-3 text-left font-medium text-muted-foreground">上傳時間</th>
                <th className="px-4 py-3 text-left font-medium text-muted-foreground">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {items.map(a => (
                <tr key={a.id} className="hover:bg-muted/30 transition-colors">
                  <td className="px-4 py-3"><AssetIcon type={a.asset_type} /></td>
                  <td className="px-4 py-3">
                    <p className="font-medium">{a.title || a.original_filename}</p>
                    {a.alt_text && <p className="text-xs text-muted-foreground">{a.alt_text}</p>}
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">{fmtSize(a.file_size_bytes)}</td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap gap-1">
                      {a.is_indexable && <Badge variant="outline" className="text-xs bg-green-50 text-green-700">可索引</Badge>}
                      {!a.is_indexable && <Badge variant="outline" className="text-xs text-muted-foreground">不索引</Badge>}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-muted-foreground text-xs">{new Date(a.created_at).toLocaleDateString("zh-TW")}</td>
                  <td className="px-4 py-3">
                    {a.public_url && (
                      <a href={a.public_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-primary hover:underline text-xs">
                        <ExternalLink className="h-3 w-3" />檢視
                      </a>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {meta && meta.total_pages > 1 && (
        <div className="mt-4 flex items-center justify-between">
          <p className="text-sm text-muted-foreground">第 {page} / {meta.total_pages} 頁</p>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>上一頁</Button>
            <Button variant="outline" size="sm" disabled={page >= meta.total_pages} onClick={() => setPage(p => p + 1)}>下一頁</Button>
          </div>
        </div>
      )}
    </div>
  );
}
