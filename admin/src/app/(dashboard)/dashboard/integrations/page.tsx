import Link from "next/link";
import { LockKeyhole, LifeBuoy } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function IntegrationsPage() {
  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div><h1 className="text-2xl font-bold tracking-tight">外部服務設定</h1><p className="mt-1 text-sm text-muted-foreground">外部服務由 ForgeBase 團隊統一設定與維護，避免金鑰外洩或錯誤連線影響正式網站。</p></div>
      <Card>
        <CardHeader><CardTitle className="flex items-center gap-2 text-base"><LockKeyhole className="h-5 w-5 text-primary" />此區由 ForgeBase 管理</CardTitle><CardDescription>Email 寄送、搜尋資料、追蹤碼與其他第三方服務，會依已確認的交付範圍設定。</CardDescription></CardHeader>
        <CardContent className="space-y-4 text-sm text-muted-foreground">
          <p>租戶後台不顯示或要求填寫技術憑證，避免設定錯誤或意外外洩。</p>
          <p>如需新增、替換或確認外部服務，請提交修改需求，由 ForgeBase 團隊檢查授權、資料範圍與正式環境設定。</p>
          <Button asChild><Link href="/dashboard/support"><LifeBuoy className="h-4 w-4" />前往網站修改與支援</Link></Button>
        </CardContent>
      </Card>
    </div>
  );
}
