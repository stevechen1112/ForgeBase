"use client";

import { ArrowDown, ArrowUp, Plus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

type PageBlock = { type: string; [key: string]: unknown };

type Props = {
  value: string;
  onChange: (value: string) => void;
};

const BLOCK_TYPES = [
  { value: "hero", label: "首頁主視覺" },
  { value: "rich-text", label: "文字內容" },
  { value: "feature-grid", label: "特色卡片" },
  { value: "stats", label: "數字成果" },
  { value: "checklist", label: "重點清單" },
  { value: "split", label: "圖文並排" },
  { value: "cta", label: "行動呼籲" },
  { value: "contact-form", label: "聯絡表單" },
  { value: "contact-cards", label: "聯絡資訊卡" },
] as const;

const SELECT_CLS = "flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring";

function parseBlocks(value: string): PageBlock[] | null {
  if (!value.trim()) return null;
  try {
    const parsed = JSON.parse(value) as unknown;
    const candidate = Array.isArray(parsed)
      ? parsed
      : parsed && typeof parsed === "object" && Array.isArray((parsed as { blocks?: unknown }).blocks)
        ? (parsed as { blocks: unknown[] }).blocks
        : null;
    if (!candidate || candidate.some((item) => !item || typeof item !== "object" || Array.isArray(item))) return null;
    return candidate.map((item) => ({ ...(item as Record<string, unknown>), type: String((item as Record<string, unknown>).type || "rich-text") }));
  } catch {
    return null;
  }
}

function stringValue(value: unknown): string {
  return typeof value === "string" ? value : "";
}

function objectValue(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : {};
}

function arrayValue(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

function newBlock(type = "rich-text"): PageBlock {
  if (type === "feature-grid" || type === "contact-cards") return { type, title: "", description: "", items: [] };
  if (type === "stats" || type === "checklist") return { type, title: "", items: [] };
  if (type === "cta") return { type, title: "", description: "", primaryCta: { label: "", href: "/contact" } };
  if (type === "rich-text") return { type, title: "", content: "" };
  return { type, title: "", description: "" };
}

export function PageBlocksEditor({ value, onChange }: Props) {
  const blocks = parseBlocks(value);

  if (blocks === null) {
    const containsMarkup = /<\/?[a-z][^>]*>/i.test(value);
    if (containsMarkup) {
      return (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-950">
          <p className="font-medium">這個頁面使用交付時製作的特殊版型</p>
          <p className="mt-1 leading-6 text-amber-900">
            為避免誤改排版，系統不顯示程式內容。您仍可修改頁面名稱、摘要、主圖與上架狀態；若要調整這段版面，請從「網站修改與支援」提出需求。
          </p>
        </div>
      );
    }
    return (
      <div className="space-y-3">
        <Textarea
          value={value}
          onChange={(event) => onChange(event.target.value)}
          rows={12}
          placeholder="輸入這個頁面要呈現的文字內容……"
        />
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-md border bg-muted/20 px-3 py-2">
          <p className="text-xs text-muted-foreground">適合一般文字頁；需要主視覺、卡片或表單時，可改用區塊編輯。</p>
          <Button type="button" size="sm" variant="outline" onClick={() => onChange(JSON.stringify([newBlock("rich-text")]))}>
            改用區塊編輯
          </Button>
        </div>
      </div>
    );
  }

  const emit = (next: PageBlock[]) => onChange(JSON.stringify(next));
  const updateBlock = (index: number, patch: Record<string, unknown>) => emit(blocks.map((block, current) => current === index ? { ...block, ...patch } : block));
  const removeBlock = (index: number) => emit(blocks.filter((_, current) => current !== index));
  const moveBlock = (index: number, direction: -1 | 1) => {
    const target = index + direction;
    if (target < 0 || target >= blocks.length) return;
    const next = [...blocks];
    [next[index], next[target]] = [next[target], next[index]];
    emit(next);
  };

  const updateItems = (blockIndex: number, items: unknown[]) => updateBlock(blockIndex, { items });

  return (
    <div className="space-y-4">
      {blocks.length === 0 && <p className="rounded-md border bg-muted/20 px-3 py-4 text-sm text-muted-foreground">尚無內容區塊。</p>}
      {blocks.map((block, index) => {
        const items = arrayValue(block.items);
        const primaryCta = objectValue(block.primaryCta);
        return (
          <section key={`${index}-${block.type}`} className="space-y-4 rounded-xl border bg-card p-4 shadow-sm">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary/10 text-xs font-semibold text-primary">{index + 1}</span>
                <select className={SELECT_CLS} value={block.type} onChange={(event) => updateBlock(index, { type: event.target.value })}>
                  {BLOCK_TYPES.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
                </select>
              </div>
              <div className="flex items-center gap-1">
                <Button type="button" size="icon" variant="ghost" aria-label="向上移動" disabled={index === 0} onClick={() => moveBlock(index, -1)}><ArrowUp className="h-4 w-4" /></Button>
                <Button type="button" size="icon" variant="ghost" aria-label="向下移動" disabled={index === blocks.length - 1} onClick={() => moveBlock(index, 1)}><ArrowDown className="h-4 w-4" /></Button>
                <Button type="button" size="icon" variant="ghost" aria-label="刪除區塊" className="text-destructive" onClick={() => removeBlock(index)}><Trash2 className="h-4 w-4" /></Button>
              </div>
            </div>

            <div className="grid gap-3 md:grid-cols-2">
              <div className="space-y-1.5"><Label>小標</Label><Input value={stringValue(block.eyebrow)} onChange={(event) => updateBlock(index, { eyebrow: event.target.value })} /></div>
              <div className="space-y-1.5"><Label>標題</Label><Input value={stringValue(block.title)} onChange={(event) => updateBlock(index, { title: event.target.value })} /></div>
            </div>

            {!["rich-text", "stats"].includes(block.type) && (
              <div className="space-y-1.5"><Label>說明</Label><Textarea rows={3} value={stringValue(block.description)} onChange={(event) => updateBlock(index, { description: event.target.value })} /></div>
            )}

            {block.type === "rich-text" && (
              <div className="space-y-1.5"><Label>內文</Label><Textarea rows={8} value={stringValue(block.content)} onChange={(event) => updateBlock(index, { content: event.target.value })} /></div>
            )}

            {block.type === "split" && (
              <div className="grid gap-3 md:grid-cols-2">
                <div className="space-y-1.5 md:col-span-2"><Label>內文</Label><Textarea rows={6} value={stringValue(block.content)} onChange={(event) => updateBlock(index, { content: event.target.value })} /></div>
                <div className="space-y-1.5"><Label>圖片網址</Label><Input value={stringValue(block.imageUrl)} onChange={(event) => updateBlock(index, { imageUrl: event.target.value })} /></div>
                <div className="space-y-1.5"><Label>圖片替代文字</Label><Input value={stringValue(block.imageAlt)} onChange={(event) => updateBlock(index, { imageAlt: event.target.value })} /></div>
              </div>
            )}

            {block.type === "hero" && (
              <div className="space-y-1.5"><Label>背景圖片網址</Label><Input value={stringValue(block.backgroundImageUrl)} onChange={(event) => updateBlock(index, { backgroundImageUrl: event.target.value })} /></div>
            )}

            {["hero", "cta", "split"].includes(block.type) && (
              <div className="grid gap-3 rounded-lg border bg-muted/20 p-3 md:grid-cols-2">
                <div className="space-y-1.5"><Label>主要按鈕文字</Label><Input value={stringValue(primaryCta.label)} onChange={(event) => updateBlock(index, { primaryCta: { ...primaryCta, label: event.target.value } })} /></div>
                <div className="space-y-1.5"><Label>主要按鈕連結</Label><Input value={stringValue(primaryCta.href)} onChange={(event) => updateBlock(index, { primaryCta: { ...primaryCta, href: event.target.value } })} /></div>
              </div>
            )}

            {["feature-grid", "contact-cards"].includes(block.type) && (
              <div className="space-y-2">
                <Label>{block.type === "feature-grid" ? "卡片內容" : "聯絡資訊"}</Label>
                {items.map((rawItem, itemIndex) => {
                  const item = objectValue(rawItem);
                  return <div key={itemIndex} className="grid gap-2 rounded-lg border p-3 md:grid-cols-[1fr_1.5fr_auto]">
                    <Input placeholder="標題" value={stringValue(item.title)} onChange={(event) => updateItems(index, items.map((entry, current) => current === itemIndex ? { ...item, title: event.target.value } : entry))} />
                    <Input placeholder="說明" value={stringValue(item.description)} onChange={(event) => updateItems(index, items.map((entry, current) => current === itemIndex ? { ...item, description: event.target.value } : entry))} />
                    <Button type="button" size="icon" variant="ghost" className="text-destructive" aria-label="刪除卡片" onClick={() => updateItems(index, items.filter((_, current) => current !== itemIndex))}><Trash2 className="h-4 w-4" /></Button>
                  </div>;
                })}
                <Button type="button" size="sm" variant="outline" onClick={() => updateItems(index, [...items, { title: "", description: "" }])}><Plus className="h-4 w-4" />新增一項</Button>
              </div>
            )}

            {block.type === "stats" && (
              <div className="space-y-2">
                <Label>數字成果</Label>
                {items.map((rawItem, itemIndex) => {
                  const item = objectValue(rawItem);
                  return <div key={itemIndex} className="grid gap-2 rounded-lg border p-3 md:grid-cols-[1fr_1.5fr_auto]">
                    <Input placeholder="數字，例如 98%" value={stringValue(item.value)} onChange={(event) => updateItems(index, items.map((entry, current) => current === itemIndex ? { ...item, value: event.target.value } : entry))} />
                    <Input placeholder="說明" value={stringValue(item.label)} onChange={(event) => updateItems(index, items.map((entry, current) => current === itemIndex ? { ...item, label: event.target.value } : entry))} />
                    <Button type="button" size="icon" variant="ghost" className="text-destructive" aria-label="刪除數字" onClick={() => updateItems(index, items.filter((_, current) => current !== itemIndex))}><Trash2 className="h-4 w-4" /></Button>
                  </div>;
                })}
                <Button type="button" size="sm" variant="outline" onClick={() => updateItems(index, [...items, { value: "", label: "" }])}><Plus className="h-4 w-4" />新增數字</Button>
              </div>
            )}

            {block.type === "checklist" && (
              <div className="space-y-2">
                <Label>重點清單</Label>
                {items.map((item, itemIndex) => <div key={itemIndex} className="flex gap-2"><Input value={stringValue(item)} onChange={(event) => updateItems(index, items.map((entry, current) => current === itemIndex ? event.target.value : entry))} /><Button type="button" size="icon" variant="ghost" className="text-destructive" aria-label="刪除重點" onClick={() => updateItems(index, items.filter((_, current) => current !== itemIndex))}><Trash2 className="h-4 w-4" /></Button></div>)}
                <Button type="button" size="sm" variant="outline" onClick={() => updateItems(index, [...items, ""])}><Plus className="h-4 w-4" />新增重點</Button>
              </div>
            )}
          </section>
        );
      })}
      <Button type="button" variant="outline" onClick={() => emit([...blocks, newBlock()])}><Plus className="h-4 w-4" />新增內容區塊</Button>
    </div>
  );
}
