"use client";

import { useState } from "react";
import { SendHorizonal } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

interface ChatInputProps {
  disabled?: boolean;
  onSubmit: (value: string) => Promise<void>;
}

export function ChatInput({ disabled = false, onSubmit }: ChatInputProps) {
  const [value, setValue] = useState("");

  async function handleSubmit() {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    setValue("");
    await onSubmit(trimmed);
  }

  return (
    <div className="border-t border-slate-200 bg-white p-3">
      <div className="flex items-end gap-2">
        <Textarea
          value={value}
          onChange={(event) => setValue(event.target.value)}
          placeholder="Ask about material, MOQ, OEM, or certification..."
          className="min-h-[72px] resize-none border-slate-200"
          maxLength={500}
          disabled={disabled}
          onKeyDown={(event) => {
            if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
              event.preventDefault();
              void handleSubmit();
            }
          }}
        />
        <Button
          type="button"
          size="icon"
          onClick={() => void handleSubmit()}
          disabled={disabled || !value.trim()}
          aria-label="Send message"
        >
          <SendHorizonal />
        </Button>
      </div>
    </div>
  );
}