<#
.SYNOPSIS
  Deploy ForgeBase sales landing page to sales.mitselect.com
.DESCRIPTION
  1. Syncs HTML + assets to /opt/forgebase/sales/ on the server
  2. Links Nginx config
  3. Obtains SSL cert (first run only)
  4. Reloads Nginx
.NOTES
  Prerequisites:
  - DNS A record: sales.mitselect.com -> server IP
  - SSH access to the server
  - certbot installed on the server
#>

param(
    [string]$Server = "mitselect.com",
    [string]$User   = "root",
    [string]$SshKey  = ""
)

$ErrorActionPreference = "Stop"

# --- Config ---
$RemoteDir  = "/opt/forgebase/sales"
$NginxConf  = "/etc/nginx/sites-enabled/sales.mitselect.com.conf"
$LocalRoot  = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)  # repo root

$SshTarget = if ($User) { "$User@$Server" } else { $Server }
$SshArgs   = if ($SshKey) { @("-i", $SshKey) } else { @() }

function Invoke-Ssh {
    param([string]$Cmd)
    Write-Host "[SSH] $Cmd" -ForegroundColor Cyan
    ssh @SshArgs $SshTarget $Cmd
    if ($LASTEXITCODE -ne 0) { throw "SSH command failed: $Cmd" }
}

function Invoke-Scp {
    param([string]$Local, [string]$Remote)
    Write-Host "[SCP] $Local -> $Remote" -ForegroundColor Cyan
    scp -r @SshArgs $Local "${SshTarget}:${Remote}"
    if ($LASTEXITCODE -ne 0) { throw "SCP failed: $Local -> $Remote" }
}

# --- Step 1: Create remote directory ---
Write-Host "`n=== Step 1: Prepare remote directory ===" -ForegroundColor Green
Invoke-Ssh "mkdir -p $RemoteDir/assets/sales-page/generated"

# --- Step 2: Upload HTML (rename to index.html) ---
Write-Host "`n=== Step 2: Upload HTML ===" -ForegroundColor Green
Invoke-Scp "$LocalRoot\forgebase-homepage.html" "$RemoteDir/index.html"

# --- Step 3: Upload image assets ---
Write-Host "`n=== Step 3: Upload image assets ===" -ForegroundColor Green
Invoke-Scp "$LocalRoot\assets\sales-page\generated\*.jpg" "$RemoteDir/assets/sales-page/generated/"

# --- Step 4: Upload & link Nginx config ---
Write-Host "`n=== Step 4: Configure Nginx ===" -ForegroundColor Green
Invoke-Scp "$LocalRoot\infra\nginx_sales.conf" "/tmp/nginx_sales.conf"
Invoke-Ssh "cp /tmp/nginx_sales.conf $NginxConf"

# --- Step 5: Test Nginx config ---
Write-Host "`n=== Step 5: Test Nginx ===" -ForegroundColor Green
Invoke-Ssh "nginx -t"

# --- Step 6: SSL certificate (skip if already exists) ---
Write-Host "`n=== Step 6: SSL Certificate ===" -ForegroundColor Green
$certCheck = ssh @SshArgs $SshTarget "test -f /etc/letsencrypt/live/sales.mitselect.com/fullchain.pem && echo EXISTS || echo MISSING"
if ($certCheck -eq "MISSING") {
    Write-Host "Obtaining SSL certificate via certbot..." -ForegroundColor Yellow
    # Temporarily comment out SSL lines for initial cert request
    Invoke-Ssh "sed -i 's/listen 443 ssl;/# listen 443 ssl;/' $NginxConf"
    Invoke-Ssh "sed -i 's/ssl_/#ssl_/' $NginxConf"
    Invoke-Ssh "nginx -s reload"
    Invoke-Ssh "certbot --nginx -d sales.mitselect.com --non-interactive --agree-tos --redirect"
} else {
    Write-Host "SSL certificate already exists, skipping." -ForegroundColor Gray
    Invoke-Ssh "nginx -s reload"
}

# --- Done ---
Write-Host "`n=== Deployment Complete ===" -ForegroundColor Green
Write-Host "  URL: https://sales.mitselect.com" -ForegroundColor White
Write-Host "  Files served from: $RemoteDir" -ForegroundColor White
Write-Host ""
Write-Host "DNS reminder: Ensure A record for sales.mitselect.com points to your server IP." -ForegroundColor Yellow
