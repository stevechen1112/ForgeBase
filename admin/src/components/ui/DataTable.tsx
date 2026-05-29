"use client";
/**
 * Generic paginated data table for admin list pages.
 * Uses shadcn/ui Table, Input, Button, Badge primitives.
 */
import { useState, useMemo } from "react";
import Link from "next/link";
import { Search, ArrowUpDown, ArrowUp, ArrowDown, Pencil, Trash2, Loader2, PackageOpen, Check, X } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { cn } from "@/lib/utils";

export type Column<T> = {
  key: keyof T | string;
  label: string;
  render?: (value: unknown, row: T) => React.ReactNode;
  className?: string;
  sortable?: boolean;
};

type SortDir = "asc" | "desc";

type Props<T extends { id: string }> = {
  columns: Column<T>[];
  rows: T[];
  editBasePath: string;
  onDelete?: (id: string) => void;
  isDeleting?: string | null;
  searchPlaceholder?: string;
  extraActions?: (row: T) => React.ReactNode;
};

export function DataTable<T extends { id: string }>({
  columns,
  rows,
  editBasePath,
  onDelete,
  isDeleting,
  searchPlaceholder = "搜尋…",
  extraActions,
}: Props<T>) {
  const [query, setQuery]     = useState("");
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<SortDir>("asc");
  const [pendingDelete, setPendingDelete] = useState<string | null>(null);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return rows;
    return rows.filter((row) =>
      columns.some((col) => {
        const v = (row as Record<string, unknown>)[String(col.key)];
        return String(v ?? "").toLowerCase().includes(q);
      }),
    );
  }, [rows, query, columns]);

  const sorted = useMemo(() => {
    if (!sortKey) return filtered;
    return [...filtered].sort((a, b) => {
      const av = String((a as Record<string, unknown>)[sortKey] ?? "");
      const bv = String((b as Record<string, unknown>)[sortKey] ?? "");
      const cmp = av.localeCompare(bv, undefined, { numeric: true });
      return sortDir === "asc" ? cmp : -cmp;
    });
  }, [filtered, sortKey, sortDir]);

  function toggleSort(key: string) {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("asc");
    }
  }

  function SortIcon({ colKey }: { colKey: string }) {
    if (sortKey !== colKey) return <ArrowUpDown className="ml-1.5 h-3.5 w-3.5 opacity-30" />;
    return sortDir === "asc"
      ? <ArrowUp className="ml-1.5 h-3.5 w-3.5 text-primary" />
      : <ArrowDown className="ml-1.5 h-3.5 w-3.5 text-primary" />;
  }

  return (
    <div className="space-y-4">
      {/* ─── Toolbar ─── */}
      <div className="flex items-center justify-between gap-3">
        <div className="relative w-full max-w-xs">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={searchPlaceholder}
            className="pl-9 h-9 text-sm"
          />
        </div>
        <span className="shrink-0 text-xs text-muted-foreground tabular-nums">
          {sorted.length} / {rows.length} 筆
        </span>
      </div>

      {/* ─── Table ─── */}
      <div className="rounded-lg border bg-background shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow className="bg-muted/50 hover:bg-muted/50">
                {columns.map((col) => (
                  <TableHead
                    key={String(col.key)}
                    className={cn(
                      "text-xs font-semibold uppercase tracking-wide text-muted-foreground",
                      col.sortable !== false && "cursor-pointer select-none hover:text-foreground",
                      col.className,
                    )}
                    onClick={col.sortable !== false ? () => toggleSort(String(col.key)) : undefined}
                  >
                    <span className="inline-flex items-center">
                      {col.label}
                      {col.sortable !== false && <SortIcon colKey={String(col.key)} />}
                    </span>
                  </TableHead>
                ))}
                <TableHead className="text-right text-xs font-semibold uppercase tracking-wide text-muted-foreground w-28">
                  操作
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {sorted.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={columns.length + 1} className="py-20 text-center">
                    <div className="flex flex-col items-center gap-3 text-muted-foreground">
                      <PackageOpen className="h-10 w-10 opacity-40" />
                      <p className="text-sm font-medium">
                        {query ? `找不到符合「${query}」的結果` : "目前沒有資料"}
                      </p>
                      {query && (
                        <Button variant="ghost" size="sm" onClick={() => setQuery("")} className="text-xs">
                          清除搜尋
                        </Button>
                      )}
                    </div>
                  </TableCell>
                </TableRow>
              ) : (
                sorted.map((row) => (
                  <TableRow key={row.id} className="group hover:bg-muted/30 transition-colors">
                    {columns.map((col) => {
                      const rawVal = (row as Record<string, unknown>)[String(col.key)];
                      return (
                        <TableCell key={String(col.key)} className={cn("text-sm", col.className)}>
                          {col.render ? col.render(rawVal, row) : String(rawVal ?? "")}
                        </TableCell>
                      );
                    })}
                    <TableCell>
                      {pendingDelete === row.id ? (
                        <div className="flex items-center justify-end gap-1">
                          <span className="text-xs text-muted-foreground mr-0.5">確認刪除？</span>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-7 w-7 text-destructive hover:text-destructive hover:bg-destructive/10"
                            onClick={() => { onDelete?.(row.id); setPendingDelete(null); }}
                            disabled={isDeleting === row.id}
                            aria-label="確認刪除"
                          >
                            {isDeleting === row.id ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Check className="h-3.5 w-3.5" />}
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-7 w-7"
                            onClick={() => setPendingDelete(null)}
                            aria-label="取消"
                          >
                            <X className="h-3.5 w-3.5" />
                          </Button>
                        </div>
                      ) : (
                        <div className="flex items-center justify-end gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                          {extraActions?.(row)}
                          <Button variant="ghost" size="icon" className="h-7 w-7 text-muted-foreground hover:text-primary" asChild>
                            <Link href={`${editBasePath}/${row.id}/edit`} aria-label="編輯">
                              <Pencil className="h-3.5 w-3.5" />
                            </Link>
                          </Button>
                          {onDelete && (
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-7 w-7 text-muted-foreground hover:text-destructive"
                              onClick={() => setPendingDelete(row.id)}
                              aria-label="刪除"
                            >
                              <Trash2 className="h-3.5 w-3.5" />
                            </Button>
                          )}
                        </div>
                      )}
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>
      </div>
    </div>
  );
}

