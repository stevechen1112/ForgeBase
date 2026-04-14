"use client";
import { useEffect, useState, useCallback } from "react";
import { useAuth } from "@/lib/auth/store";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { RefreshCw, AlertTriangle, Link2, Package, Globe, HelpCircle } from "lucide-react";
import Link from "next/link";
import { API_BASE, buildApiHeaders } from "@/lib/api/client";

type Orphans = { orphan_products: number; orphan_applications: number; orphan_faqs: number };
type Product = { id: string; product_name: string; slug: string; category_id: string | null; status: string };
type FAQ = { id: string; question: string; status: string };

export default function RelationsPage() {
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";

  const [orphans, setOrphans] = useState<Orphans | null>(null);
  const [orphanProducts, setOrphanProducts] = useState<Product[]>([]);
  const [orphanFaqs, setOrphanFaqs] = useState<FAQ[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    setLoading(true); setError(null);
    const h = buildApiHeaders(token);
    Promise.all([
      fetch(`${API_BASE}/content/entities/orphans`, { headers: h }).then(r => r.json()),
      fetch(`${API_BASE}/content/entities/orphans/products`, { headers: h }).then(r => r.json()),
      fetch(`${API_BASE}/content/entities/orphans/faqs`, { headers: h }).then(r => r.json()),
    ])
      .then(([summary, prods, faqs]) => {
        setOrphans(summary);
        setOrphanProducts(Array.isArray(prods?.data) ? prods.data : Array.isArray(prods) ? prods : []);
        setOrphanFaqs(Array.isArray(faqs?.data) ? faqs.data : Array.isArray(faqs) ? faqs : []);
      })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, [token]);

  useEffect(() => { load(); }, [load]);

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Entity 關聯管理</h1>
          <p className="mt-0.5 text-sm text-muted-foreground">管理商品、應用場景、認證、FAQ 之間的多對多關聯，並修復孤立 entity</p>
        </div>
        <Button variant="outline" size="sm" onClick={load} disabled={loading}>
          <RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />重新整理
        </Button>
      </div>

      {error && <Alert variant="destructive" className="mb-4"><AlertDescription>{error}</AlertDescription></Alert>}

      {/* Orphan Summary */}
      {orphans && (
        <div className="mb-6 grid grid-cols-3 gap-4">
          {[
            { label: "孤立商品", count: orphans.orphan_products, icon: Package, color: "text-orange-500", bg: "bg-orange-50 border-orange-200", href: "/dashboard/products" },
            { label: "孤立應用場景", count: orphans.orphan_applications, icon: Globe, color: "text-blue-500", bg: "bg-blue-50 border-blue-200", href: "/dashboard/applications" },
            { label: "孤立 FAQ", count: orphans.orphan_faqs, icon: HelpCircle, color: "text-purple-500", bg: "bg-purple-50 border-purple-200", href: "/dashboard/faqs" },
          ].map(({ label, count, icon: Icon, color, bg, href }) => (
            <div key={label} className={`rounded-lg border p-4 ${count > 0 ? bg : "bg-muted/30 border-border"}`}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Icon className={`h-5 w-5 ${count > 0 ? color : "text-muted-foreground"}`} />
                  <span className="text-sm font-medium">{label}</span>
                </div>
                {count > 0 ? (
                  <Badge className="bg-orange-100 text-orange-700 hover:bg-orange-100">
                    <AlertTriangle className="mr-1 h-3 w-3" />{count}
                  </Badge>
                ) : (
                  <Badge variant="outline" className="text-green-600">✓ 已連結</Badge>
                )}
              </div>
              {count > 0 && (
                <p className="mt-2 text-xs text-muted-foreground">
                  {count} 個 {label}未與任何其他 entity 建立關聯，建議前往{" "}
                  <Link href={href} className="text-primary hover:underline">編輯介面</Link>設定關聯
                </p>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Orphan Products List */}
      {orphanProducts.length > 0 && (
        <div className="mb-6">
          <h2 className="mb-3 flex items-center gap-2 text-base font-semibold">
            <AlertTriangle className="h-4 w-4 text-orange-500" />孤立商品（{orphanProducts.length}）
          </h2>
          <div className="rounded-lg border">
            <table className="w-full text-sm">
              <thead className="bg-muted/50">
                <tr>
                  <th className="px-4 py-2 text-left font-medium text-muted-foreground">商品名稱</th>
                  <th className="px-4 py-2 text-left font-medium text-muted-foreground">Slug</th>
                  <th className="px-4 py-2 text-left font-medium text-muted-foreground">狀態</th>
                  <th className="px-4 py-2 text-left font-medium text-muted-foreground">操作</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {orphanProducts.slice(0, 10).map(p => (
                  <tr key={p.id} className="hover:bg-muted/30">
                    <td className="px-4 py-2 font-medium">{p.product_name}</td>
                    <td className="px-4 py-2 text-muted-foreground text-xs font-mono">{p.slug}</td>
                    <td className="px-4 py-2"><Badge variant="outline" className="text-xs">{p.status}</Badge></td>
                    <td className="px-4 py-2">
                      <Link href={`/dashboard/products/${p.id}/edit`} className="text-primary text-xs hover:underline">設定關聯</Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Orphan FAQs List */}
      {orphanFaqs.length > 0 && (
        <div className="mb-6">
          <h2 className="mb-3 flex items-center gap-2 text-base font-semibold">
            <AlertTriangle className="h-4 w-4 text-purple-500" />孤立 FAQ（{orphanFaqs.length}）
          </h2>
          <div className="rounded-lg border">
            <table className="w-full text-sm">
              <thead className="bg-muted/50">
                <tr>
                  <th className="px-4 py-2 text-left font-medium text-muted-foreground">問題</th>
                  <th className="px-4 py-2 text-left font-medium text-muted-foreground">狀態</th>
                  <th className="px-4 py-2 text-left font-medium text-muted-foreground">操作</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {orphanFaqs.slice(0, 10).map((f: FAQ) => (
                  <tr key={f.id} className="hover:bg-muted/30">
                    <td className="px-4 py-2 font-medium max-w-md truncate">{f.question}</td>
                    <td className="px-4 py-2"><Badge variant="outline" className="text-xs">{f.status}</Badge></td>
                    <td className="px-4 py-2">
                      <Link href={`/dashboard/faqs/${f.id}/edit`} className="text-primary text-xs hover:underline">設定關聯</Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {orphans && orphans.orphan_products === 0 && orphans.orphan_applications === 0 && orphans.orphan_faqs === 0 && (
        <div className="rounded-lg border-2 border-dashed border-muted p-12 text-center">
          <Link2 className="mx-auto mb-3 h-10 w-10 text-green-500 opacity-70" />
          <p className="font-semibold text-green-700">所有 Entity 均已建立關聯</p>
          <p className="mt-1 text-sm text-muted-foreground">系統未偵測到孤立的商品、應用場景或 FAQ</p>
        </div>
      )}
    </div>
  );
}
