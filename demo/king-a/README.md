# King-A (欣榮貿易) — ForgeBase Intake Demo Package

本資料夾是透過 **Legacy Site Intake** 模組，從 `king-a.com.tw` 自動採集並結構化的導入套件。

## 公司資訊

- **公司名稱**：欣榮貿易有限公司
- **英文名稱**：King-A Trading Co., Ltd.
- **定位**：Panasonic 焊接設備代理商 / 工業自動化解決方案供應商
- **主要產品線**：焊接機械手臂、焊接機（CO2/MAG/MIG/TIG）、雷射焊切設備、離子切割機、工業接著劑
- **目標市場**：台灣製造業、金屬加工廠、自動化整合商

## 資料來源

- 原始網站：https://king-a.com.tw/
- 爬取時間：2026-03-31
- 爬取頁數：54 頁
- 抽取實體：52 個產品/類別候選

## 資料夾結構

```
king-a/
├── README.md
├── content/
│   └── 01-company-blueprint.md
├── seed/
│   ├── manifest.json
│   ├── categories.json
│   ├── products.json
│   ├── applications.json
│   ├── faq-items.json
│   ├── pages.json
│   ├── relationships.json
│   └── import_king_a_content.py   ← 自動匯入腳本
├── docker-compose.yml             ← 獨立部署配置
├── deploy-kinga.ps1               ← 一鍵部署腳本
├── env.example                    ← 環境變數模板
├── nginx_kinga.conf               ← Nginx 配置
└── assets/
    └── (placeholder for images)
```

## 獨立部署（與 demo 完全隔離）

King-A 使用獨立的 DB、API、Web、Admin，port 全部與 demo 錯開：

| 服務 | Demo (mitselect.com) | King-A |
|------|---------------------|--------|
| DB   | 5432                | **5433** |
| API  | 8000                | **8001** |
| Web  | 3000                | **3002** |
| Admin| 3001                | **3003** |

### 快速啟動

```powershell
cd demo\king-a
Copy-Item env.example .env        # 複製並編輯環境變數
.\deploy-kinga.ps1                # 一鍵部署
```

### 手動啟動

```powershell
cd demo\king-a
Copy-Item env.example .env
docker compose up -d --build
# 等待 DB + API 就緒後：
docker compose exec api-kinga alembic upgrade head
docker compose exec api-kinga python seed_admin.py
docker compose exec api-kinga python /app/../demo/king-a/seed/import_king_a_content.py
```

### 部署到正式環境

1. 複製 `nginx_kinga.conf` 到 `/etc/nginx/sites-available/`
2. `certbot --nginx -d king-a-growth.com`
3. 更新 `.env` 中的域名與 API key

## 導入順序（Seed）

1. `pages.json`
2. `categories.json`
3. `products.json`
4. `applications.json`
5. `faq-items.json`
6. `relationships.json`

## Pilot 建議

優先導入 **Panasonic 焊接機械手臂 + 焊接機** 產品線（約 25 個產品），
這條線內容最深、型號最清楚、最有商業轉換潛力。
