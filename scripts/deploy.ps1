#!/usr/bin/env pwsh
# ForgeBase 一鍵部署腳本 — 從本機 SSH 到 Linode 執行完整部署
$ErrorActionPreference = "Continue"
$SSH = "ssh -i $env:USERPROFILE\.ssh\id_rsa_linode root@172.234.81.223"

function Step($msg) { Write-Host "`n>>> $msg" -ForegroundColor Cyan }

# 0. 先 push 到 GitHub
Step "Pushing to GitHub..."
git push origin main
if ($LASTEXITCODE -ne 0) { Write-Host "git push failed" -ForegroundColor Red; exit 1 }

# 1. Pull code on server
Step "Pulling latest code on server..."
Invoke-Expression "$SSH 'cd /opt/forgebase/app && git checkout -- . && git pull origin main'" 2>&1 | Out-String | Write-Host

# 2. API: deps + migrations + restart
Step "Updating API (deps + migrations + restart)..."
Invoke-Expression "$SSH 'cd /opt/forgebase/app/api && source .venv/bin/activate && pip install -r requirements.txt --quiet && alembic upgrade head 2>&1; systemctl restart forgebase-api && sleep 2 && systemctl is-active forgebase-api'" 2>&1 | Out-String | Write-Host

# 3. Admin: build + restart
Step "Building admin frontend..."
Invoke-Expression "$SSH 'cd /opt/forgebase/app/admin && npm ci --prefer-offline 2>&1 | tail -3 && npm run build 2>&1 | tail -10'" 2>&1 | Out-String | Write-Host

# 4. Web: build + restart
Step "Building web frontend..."
Invoke-Expression "$SSH 'cd /opt/forgebase/app/web && npm ci --prefer-offline 2>&1 | tail -3 && npm run build 2>&1 | tail -10'" 2>&1 | Out-String | Write-Host

# 5. Restart frontends
Step "Restarting frontend services..."
Invoke-Expression "$SSH 'systemctl restart forgebase-web forgebase-admin && sleep 5 && systemctl is-active forgebase-api forgebase-web forgebase-admin'" 2>&1 | Out-String | Write-Host

# 6. Health check
Step "Health check..."
$health = Invoke-Expression "$SSH 'curl -sf https://mitselect.com/health'" 2>&1 | Out-String
Write-Host $health
if ($health -match '"ok"') {
    Write-Host "`n=== DEPLOY SUCCESS ===" -ForegroundColor Green
} else {
    Write-Host "`n=== DEPLOY MIGHT HAVE ISSUES — check services ===" -ForegroundColor Yellow
}
