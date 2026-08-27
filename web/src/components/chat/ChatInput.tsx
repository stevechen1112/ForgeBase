"use client";

import { useState } from "react";
import { SendHorizonal } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { chatDirection, getChatUiCopy } from "@/components/chat/chat-ui-copy";

interface ChatInputProps {
  disabled?: boolean;
  locale?: string;
  onSubmit: (value: string) => Promise<void>;
}

export function ChatInput({ disabled = false, locale, onSubmit }: ChatInputProps) {
  const copy = getChatUiCopy(locale);
  const direction = chatDirection(locale);
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
          dir={direction}
          value={value}
          onChange={(event) => setValue(event.target.value)}
          placeholder={copy.placeholder}
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
          aria-label={copy.sendMessage}
        >
          <SendHorizonal />
        </Button>
      </div>
    </div>
  );
}
