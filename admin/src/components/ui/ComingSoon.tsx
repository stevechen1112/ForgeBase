"use client";
import { Construction } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useRouter } from "next/navigation";

interface Props {
  title: string;
  description?: string;
  eta?: string;
}

export function ComingSoon({ title, description, eta }: Props) {
  const router = useRouter();
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] text-center">
      <Card className="max-w-md w-full border-dashed">
        <CardContent className="pt-12 pb-10 px-8">
          <div className="mx-auto mb-5 flex h-14 w-14 items-center justify-center rounded-full bg-muted">
            <Construction className="h-7 w-7 text-muted-foreground" />
          </div>
          <Badge variant="secondary" className="mb-4">開發中</Badge>
          <h1 className="text-xl font-semibold text-foreground">{title}</h1>
          <p className="mt-2 text-sm text-muted-foreground">
            {description ?? "此功能模組正在開發中，敬請期待。"}
          </p>
          {eta && (
            <p className="mt-2 text-xs text-muted-foreground">預計上線：{eta}</p>
          )}
          <div className="mt-8 flex justify-center gap-3">
            <Button variant="outline" size="sm" onClick={() => router.back()}>
              返回
            </Button>
            <Button size="sm" onClick={() => router.push("/dashboard")}>
              回儀表板
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
