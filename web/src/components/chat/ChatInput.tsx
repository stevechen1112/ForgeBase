"use client";

import { useState } from "react";
import { SendHorizonal } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { useMessageNamespace } from "@/lib/messages";

type ChatInputMessages = {
  placeholder: string;
  sendMessage: string;
};

interface ChatInputProps {
  disabled?: boolean;
  onSubmit: (value: string) => Promise<void>;
}

export function ChatInput({ disabled = false, onSubmit }: ChatInputProps) {
  const copy = useMessageNamespace<ChatInputMessages>("chat");
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