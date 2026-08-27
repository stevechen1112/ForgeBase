"use client";

import { useMemo, useState } from "react";
import { ExternalLink, LifeBuoy, Mail } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

const SUPPORT_EMAIL = process.env.NEXT_PUBLIC_SUPPORT_EMAIL || "hello@forgebase.co";

export default function SupportPage() {
  const [requestType, setRequestType] = useState("網站內容或版面調整");
  const [subject, setSubject] = useState("");
  const [details, setDetails] = useState("");

  const mailto = useMemo(() => {
    const mailSubject = `[ForgeBase 修改需求] ${requestType}${subject.trim() ? `：${subject.trim()}` : ""}`;
    const body = `需求類型：${requestType}\n\n希望調整的頁面或功能：\n${details.trim()}\n\n請附上相關網址、圖片或文件，以便 ForgeBase 團隊確認。`;
    return `mailto:${SUPPORT_EMAIL}?subject=${encodeURIComponent(mailSubject)}&body=${encodeURIComponent(body)}`;
  }, [details, requestType, subject]);

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div>
        <h1 className="flex items-center gap-2 text-2xl font-bold tracking-tight"><LifeBuoy className="h-6 w-6 text-primary" />網站修改與支援</h1>
        <p className="mt-1 text-sm text-muted-foreground">內容可直接在後台維護；版型、網站結構、網域或外部服務設定，請交由 ForgeBase 團隊協助。</p>
      </div>

      <div className="grid gap-5 md:grid-cols-2">
        <Card>
          <CardHeader><CardTitle className="text-base">可以自行處理</CardTitle><CardDescription>儲存後即可依內容狀態更新網站。</CardDescription></CardHeader>
          <CardContent className="space-y-2 text-sm text-muted-foreground">
            <p>商品、分類與規格</p><p>一般頁面文字與圖片</p><p>應用場景、FAQ、認證與廠能</p><p>詢價案件、待辦與通知</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle className="text-base">請 ForgeBase 協助</CardTitle><CardDescription>避免影響已上線網站與追蹤資料。</CardDescription></CardHeader>
          <CardContent className="space-y-2 text-sm text-muted-foreground">
            <p>新增或大幅調整版面</p><p>導覽、頁尾與多語結構</p><p>正式網域、追蹤碼與第三方服務</p><p>大量匯入、特殊功能或資料轉換</p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader><CardTitle className="text-base">提出修改需求</CardTitle><CardDescription>系統會開啟你的 Email 軟體，寄送前仍可補充附件與收件人。</CardDescription></CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-1.5"><Label htmlFor="support-type">需求類型</Label><select id="support-type" className="flex h-10 w-full rounded-md border border-input bg-background px-3 text-sm" value={requestType} onChange={(event) => setRequestType(event.target.value)}><option>網站內容或版面調整</option><option>網域或網站上線</option><option>第三方服務或追蹤設定</option><option>資料或帳號問題</option><option>其他協助</option></select></div>
          <div className="space-y-1.5"><Label htmlFor="support-subject">簡短主旨</Label><Input id="support-subject" value={subject} onChange={(event) => setSubject(event.target.value)} placeholder="例如：更新英文首頁主視覺" maxLength={120} /></div>
          <div className="space-y-1.5"><Label htmlFor="support-details">需求說明</Label><Textarea id="support-details" value={details} onChange={(event) => setDetails(event.target.value)} rows={7} placeholder="請說明要修改的頁面、目前情況與希望完成的結果。" /></div>
          <Button type="button" disabled={!details.trim()} onClick={() => { window.location.href = mailto; }}><Mail className="h-4 w-4" />開啟 Email 寄送</Button>
          <p className="text-xs text-muted-foreground">支援信箱：{SUPPORT_EMAIL} <ExternalLink className="ml-1 inline h-3 w-3" /></p>
        </CardContent>
      </Card>
    </div>
  );
}
