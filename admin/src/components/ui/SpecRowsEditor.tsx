"use client";
import { useEffect, useRef, useState } from "react";
import { Plus, Trash2 } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";

type Row = { name: string; value: string };

type Props = {
  value: string;
  onChange: (json: string) => void;
};

function parseRows(json: string): Row[] | null {
  if (!json.trim()) return [];
  try {
    const parsed = JSON.parse(json);
    if (!Array.isArray(parsed)) return null;
    const rows: Row[] = [];
    for (const item of parsed) {
      if (typeof item !== "object" || item === null) return null;
      rows.push({
        name: typeof item.name === "string" ? item.name : "",
        value: typeof item.value === "string" ? item.value : "",
      });
    }
    return rows;
  } catch {
    return null;
  }
}

function serialize(rows: Row[]): string {
  const filled = rows.filter((r) => r.name.trim() || r.value.trim());
  return filled.length ? JSON.stringify(filled) : "";
}

export function SpecRowsEditor({ value, onChange }: Props) {
  const parsed = parseRows(value);
  const [rows, setRows] = useState<Row[]>(parsed ?? []);
  const lastSerialized = useRef(parsed ? serialize(parsed) : value);

  // 外部（如 AI 起草預填）改寫 value 時重新解析
  useEffect(() => {
    if (value === lastSerialized.current) return;
    const next = parseRows(value);
    if (next !== null) {
      setRows(next);
      lastSerialized.current = serialize(next);
    } else {
      lastSerialized.current = value;
    }
  }, [value]);

  // 內容不是規格 JSON 陣列（例如手動貼的自由文字）→ 降級為原始文字框
  if (parsed === null) {
    return (
      <div className="space-y-1.5">
        <Textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          rows={4}
          className="font-mono text-xs"
        />
        <p className="text-xs text-amber-600">
          目前內容不是規格表格格式，以原始文字模式編輯；清空後即可改用列式編輯。
        </p>
      </div>
    );
  }

  const emit = (next: Row[]) => {
    setRows(next);
    const json = serialize(next);
    lastSerialized.current = json;
    onChange(json);
  };

  const updateRow = (idx: number, field: keyof Row, v: string) => {
    emit(rows.map((r, i) => (i === idx ? { ...r, [field]: v } : r)));
  };

  return (
    <div className="space-y-2">
      {rows.length === 0 && (
        <p className="text-xs text-muted-foreground">尚無規格，點「新增規格」建立第一筆。</p>
      )}
      {rows.map((row, idx) => (
        <div key={idx} className="flex items-center gap-2">
          <Input
            value={row.name}
            onChange={(e) => updateRow(idx, "name", e.target.value)}
            placeholder="規格名稱（如 Drive Size）"
            maxLength={80}
            className="flex-1"
          />
          <Input
            value={row.value}
            onChange={(e) => updateRow(idx, "value", e.target.value)}
            placeholder="數值（如 1/2 in）"
            maxLength={200}
            className="flex-1"
          />
          <Button
            type="button"
            variant="ghost"
            size="icon"
            onClick={() => emit(rows.filter((_, i) => i !== idx))}
            aria-label="移除此規格"
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      ))}
      <Button
        type="button"
        variant="outline"
        size="sm"
        onClick={() => emit([...rows, { name: "", value: "" }])}
      >
        <Plus className="h-4 w-4" />
        新增規格
      </Button>
    </div>
  );
}
