"use client";

import { Plus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

type Dimension = {
  dimension: string;
  our_value: string;
  competitor_value: string;
  winner: "us" | "competitor" | "tie" | "";
};

type Props = {
  value: string;
  onChange: (value: string) => void;
};

const SELECT_CLS = "flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring";

function parseDimensions(value: string): Dimension[] | null {
  if (!value.trim()) return [];
  try {
    const parsed = JSON.parse(value) as unknown;
    if (!Array.isArray(parsed)) return null;
    return parsed.map((row) => {
      if (!row || typeof row !== "object" || Array.isArray(row)) throw new Error("invalid");
      const item = row as Record<string, unknown>;
      const hasCurrent =
        "dimension" in item || "our_value" in item || "competitor_value" in item || "winner" in item;
      const hasLegacy = "label" in item || "options" in item;
      if (hasLegacy && !hasCurrent) throw new Error("legacy");
      const winner = item.winner;
      return {
        dimension: typeof item.dimension === "string" ? item.dimension : "",
        our_value: typeof item.our_value === "string" ? item.our_value : "",
        competitor_value: typeof item.competitor_value === "string" ? item.competitor_value : "",
        winner: winner === "us" || winner === "competitor" || winner === "tie" ? winner : "",
      };
    });
  } catch {
    return null;
  }
}

export function ComparisonDimensionsEditor({ value, onChange }: Props) {
  const dimensions = parseDimensions(value);
  if (dimensions === null) {
    return <div className="rounded-md border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900">既有比較資料格式無法以表格顯示。資料會原樣保留，請聯繫 ForgeBase 協助轉換。</div>;
  }

  const emit = (next: Dimension[]) => onChange(next.length ? JSON.stringify(next) : "");
  const update = (index: number, patch: Partial<Dimension>) => emit(dimensions.map((row, current) => current === index ? { ...row, ...patch } : row));

  return (
    <div className="space-y-3">
      {dimensions.length === 0 && <p className="text-sm text-muted-foreground">尚無比較項目。</p>}
      {dimensions.map((row, index) => (
        <section key={index} className="space-y-3 rounded-lg border p-4">
          <div className="flex items-center gap-2">
            <Input aria-label={`比較項目 ${index + 1}`} placeholder="比較項目，例如：交期或材質" value={row.dimension} onChange={(event) => update(index, { dimension: event.target.value })} />
            <Button type="button" size="icon" variant="ghost" className="text-destructive" aria-label="刪除比較項目" onClick={() => emit(dimensions.filter((_, current) => current !== index))}><Trash2 className="h-4 w-4" /></Button>
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            <Input placeholder="我方產品或做法" value={row.our_value} onChange={(event) => update(index, { our_value: event.target.value })} />
            <Input placeholder="另一方案或一般做法" value={row.competitor_value} onChange={(event) => update(index, { competitor_value: event.target.value })} />
          </div>
          <select className={SELECT_CLS} value={row.winner} onChange={(event) => update(index, { winner: event.target.value as Dimension["winner"] })}>
            <option value="">不標示較適合者</option>
            <option value="us">我方較適合</option>
            <option value="competitor">另一方案較適合</option>
            <option value="tie">各有適用情境</option>
          </select>
        </section>
      ))}
      <Button type="button" variant="outline" onClick={() => emit([...dimensions, { dimension: "", our_value: "", competitor_value: "", winner: "" }])}><Plus className="h-4 w-4" />新增比較項目</Button>
    </div>
  );
}
