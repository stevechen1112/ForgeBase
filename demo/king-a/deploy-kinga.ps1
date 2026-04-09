#!/usr/bin/env pwsh
# ================================================================
# King-A (欣榮貿易) — ForgeBase 獨立實例一鍵部署腳本
# ================================================================
# 用途：在同一台機器上建立獨立於 demo (mitselect.com) 的 King-A 站台
# Port 配置：
#   DB   → 5433 (demo = 5432)
#   API  → 8001 (demo = 8000)
#   Web  → 3002 (demo = 3000)
#   Admin→ 3003 (demo = 3001)
#
# 執行方式：
#   cd demo\king-a
#   .\deploy-kinga.ps1
# ================================================================

$ErrorActionPreference = "Stop"
$PROJECT_ROOT = (Get-Item "$PSScriptRoot\..\..\").FullName
$KINGA_ROOT = $PSScriptRoot

function Step($msg) { Write-Host "`n>>> $msg" -ForegroundColor Cyan }
function Success($msg) { Write-Host "    ✓ $msg" -ForegroundColor Green }
function Warn($msg) { Write-Host "    ⚠ $msg" -ForegroundColor Yellow }

# ── 0. 檢查環境 ──────────────────────────────────────────
Step "檢查環境"

if (-not (Test-Path "$KINGA_ROOT\.env")) {
    if (Test-Path "$KINGA_ROOT\env.example") {
        Copy-Item "$KINGA_ROOT\env.example" "$KINGA_ROOT\.env"
        Warn ".env 檔不存在，已從 env.example 複製。請先編輯 .env 填入實際 API keys！"
        Write-Host "    路徑: $KINGA_ROOT\.env" -ForegroundColor Yellow
        $continue = Read-Host "    是否繼續部署？ (y/N)"
        if ($continue -ne "y") { exit 0 }
    } else {
        Write-Host "    ✗ 找不到 .env 或 env.example" -ForegroundColor Red
        exit 1
    }
}
Success ".env 檔案存在"

# ── 1. 啟動 Docker Compose ──────────────────────────────
Step "啟動 King-A Docker 容器 (DB + API + Web + Admin)"

Push-Location $KINGA_ROOT
docker compose up -d --build 2>&1 | Out-String | Write-Host
Pop-Location

# 等待 DB 就緒
Step "等待 PostgreSQL 就緒..."
$maxRetries = 15
for ($i = 1; $i -le $maxRetries; $i++) {
    $result = docker compose -f "$KINGA_ROOT\docker-compose.yml" exec -T db-kinga pg_isready -U forgebase_kinga 2>&1 | Out-String
    if ($result -match "accepting connections") {
        Success "PostgreSQL 已就緒 (嘗試 $i/$maxRetries)"
        break
    }
    if ($i -eq $maxRetries) {
        Write-Host "    ✗ PostgreSQL 啟動逾時" -ForegroundColor Red
        exit 1
    }
    Start-Sleep -Seconds 2
}

# ── 2. 執行 Migration ──────────────────────────────────
Step "執行 Alembic Migration..."
docker compose -f "$KINGA_ROOT\docker-compose.yml" exec -T api-kinga alembic upgrade head 2>&1 | Out-String | Write-Host
Success "Migration 完成"

# ── 3. 建立 Admin 帳號 ──────────────────────────────────
Step "建立 Admin 帳號..."
docker compose -f "$KINGA_ROOT\docker-compose.yml" exec -T api-kinga python seed_admin.py 2>&1 | Out-String | Write-Host
Success "Admin 帳號已建立"

# ── 4. 匯入 King-A 內容 ──────────────────────────────────
Step "匯入 King-A 產品內容..."

# 等待API就緒
Start-Sleep -Seconds 5
$maxRetries = 10
for ($i = 1; $i -le $maxRetries; $i++) {
    try {
        $health = Invoke-RestMethod -Uri "http://localhost:8001/health" -TimeoutSec 5
        if ($health) {
            Success "API 已就緒"
            break
        }
    } catch {
        if ($i -eq $maxRetries) {
            Warn "API 尚未就緒，繼續嘗試匯入..."
        }
        Start-Sleep -Seconds 3
    }
}

# 執行匯入腳本
docker compose -f "$KINGA_ROOT\docker-compose.yml" exec -T api-kinga python /app/../demo/king-a/seed/import_king_a_content.py 2>&1 | Out-String | Write-Host

# ── 5. 健康檢查 ──────────────────────────────────────────
Step "健康檢查..."

$services = @(
    @{Name="API";    Port=8001; Path="/health"},
    @{Name="Web";    Port=3002; Path="/"},
    @{Name="Admin";  Port=3003; Path="/"}
)

$allOk = $true
foreach ($svc in $services) {
    try {
        $resp = Invoke-WebRequest -Uri "http://localhost:$($svc.Port)$($svc.Path)" -TimeoutSec 10 -UseBasicParsing
        if ($resp.StatusCode -eq 200) {
            Success "$($svc.Name) — http://localhost:$($svc.Port) ✓"
        } else {
            Warn "$($svc.Name) — HTTP $($resp.StatusCode)"
            $allOk = $false
        }
    } catch {
        Warn "$($svc.Name) — 無法連線 http://localhost:$($svc.Port)"
        $allOk = $false
    }
}

# ── 結果 ────────────────────────────────────────────────
Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
if ($allOk) {
    Write-Host "  King-A ForgeBase 獨立實例部署成功！" -ForegroundColor Green
} else {
    Write-Host "  部署完成，但部分服務尚未就緒。請檢查 Docker logs。" -ForegroundColor Yellow
}
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  前台網站:   http://localhost:3002" -ForegroundColor White
Write-Host "  管理後台:   http://localhost:3003" -ForegroundColor White
Write-Host "  API 文件:   http://localhost:8001/docs" -ForegroundColor White
Write-Host "  PostgreSQL: localhost:5433" -ForegroundColor White
Write-Host ""
Write-Host "  與 demo (mitselect.com) 完全獨立，資料互不影響。" -ForegroundColor DarkGray
Write-Host ""
