# ForgeBase Template Demos

本子專案集中管理未串接 ForgeBase 後端的 B2B 產業網站範本。現有手工具網站仍是唯一完整串接的 Reference Site；本資料夾內的企業、產品、認證與表單資料均為 Demo。

## 目錄責任

```text
template-demos/
├─ docs/                         # 規格、作品集規劃與單一範本 Brief
│  ├─ TEMPLATE_STANDARD.md
│  ├─ PORTFOLIO.md
│  └─ templates/<slug>/
│     ├─ BRIEF.md
│     └─ ASSETS.md               # 有實際素材後才建立
├─ public/templates/<slug>/      # 瀏覽器可直接載入的範本影像
├─ scripts/                      # 合規與結構驗收
└─ src/
   ├─ app/                       # 僅放 Next.js 路由
   ├─ components/                # 跨範本共用的安全 Demo 元件
   ├─ contracts/                 # ForgeBase 共用資料契約
   └─ templates/
      ├─ registry.ts
      └─ <slug>/
         ├─ manifest.ts          # 規劃階段即建立
         ├─ data.ts              # 開始製作後建立
         └─ components/          # 該範本獨有的視覺與頁面元件
```

規劃文件不放進 `src/`，原始碼不放進 `docs/`，公開資產不放進範本原始碼資料夾。未產生素材前不建立空的 public 目錄。

## 六套範本

| Slug | 狀態 |
|---|---|
| `precision-machining` | Ready |
| `industrial-machinery` | Ready |
| `electronic-components` | Ready |
| `industrial-automation` | Ready |
| `engineering-materials` | Ready |
| `custom-packaging` | Ready |

詳細順序與能力覆蓋見 `docs/PORTFOLIO.md`。

## 本地使用

```bash
npm install
npm run dev
```

預設網址為 `http://localhost:3010`。

## 新增或製作範本

1. 在 `docs/templates/<slug>/BRIEF.md` 定義買家、購買流程、路由、資產及 ForgeBase 映射。
2. 在 `src/templates/<slug>/manifest.ts` 登記規劃狀態，不把未完成範本標成 `ready`。
3. 開始實作後建立 `data.ts` 與 `components/`，資料必須符合 `src/contracts/forgebase.ts`。
4. 實際影像放入 `public/templates/<slug>/`，並在 `docs/templates/<slug>/ASSETS.md` 記錄來源、用途、alt 與限制。
5. 在 `src/templates/registry.ts` 註冊 manifest；完成 renderer 後才加入 `registeredTemplates`。
6. 執行 `npm run compliance`，再完成桌機、手機、鍵盤與互動瀏覽器驗收。

完整規則見 `docs/TEMPLATE_STANDARD.md`。
