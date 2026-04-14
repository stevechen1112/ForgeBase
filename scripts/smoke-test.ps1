#!/usr/bin/env pwsh
<#
.SYNOPSIS
  ForgeBase Multi-Tenant Frontend Smoke Test

.DESCRIPTION
  Starts the mock SiteProfile API server + Next.js dev server, runs
  per-tenant assertion checks (title, canonical, theme, layout, robots,
  sitemap, favicon), then stops both servers.

  Pass -SkipServerStart if the servers are already running.

.PARAMETER ApiInternalUrl
  URL the Next.js server uses to call the backend API.
  Defaults to http://127.0.0.1:4010

.PARAMETER NextPort
  Port for the Next.js dev server.  Defaults to 3000.

.PARAMETER MockPort
  Port for the mock SiteProfile server.  Defaults to 4010.

.PARAMETER SkipServerStart
  Skip starting/stopping servers (use when already running).

.EXAMPLE
  .\scripts\smoke-test.ps1
  .\scripts\smoke-test.ps1 -SkipServerStart

#>
param(
  [string]$ApiInternalUrl = "http://127.0.0.1:4010",
  [int]$NextPort           = 3000,
  [int]$MockPort           = 4010,
  [switch]$SkipServerStart
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$root  = Split-Path $PSScriptRoot -Parent
$web   = Join-Path $root "web"
$scripts = Join-Path $root "scripts"

# ─── Tenant assertions config ───────────────────────────────────────────────

$tenants = @(
  @{
    Host          = "tenant-a.localhost:$NextPort"
    ExpTitle      = "Atlas Forge"
    ExpCanonical  = "https://atlasforge.example.com"
    ExpTheme      = "industrial"
    ExpLayout     = "industrial"
    ExpSitemapUrl = "https://atlasforge.example.com"
  },
  @{
    Host          = "tenant-b.localhost:$NextPort"
    ExpTitle      = "Beacon Industrial"
    ExpCanonical  = "https://beaconindustrial.example.com"
    ExpTheme      = "cobalt"
    ExpLayout     = "classic"
    ExpSitemapUrl = "https://beaconindustrial.example.com"
  }
)

# ─── Server management ──────────────────────────────────────────────────────

$mockJob = $null
$nextJob = $null

function Start-Servers {
  Write-Host "`n[smoke] Starting mock SiteProfile server on port $MockPort..." -ForegroundColor Cyan
  $script:mockJob = Start-Job -ScriptBlock {
    param($s, $p) Set-Location $s; $env:MOCK_SITE_PROFILE_PORT = $p; node "mock-site-profile-server.mjs"
  } -ArgumentList $scripts, $MockPort

  Write-Host "[smoke] Starting Next.js dev server on port $NextPort..." -ForegroundColor Cyan
  $script:nextJob = Start-Job -ScriptBlock {
    param($w, $u, $p) Set-Location $w; $env:API_INTERNAL_URL = $u; $env:PORT = $p; npm run dev -- --port $p
  } -ArgumentList $web, $ApiInternalUrl, $NextPort

  Write-Host "[smoke] Waiting for Next.js to be ready (up to 60s)..."
  $deadline = (Get-Date).AddSeconds(60)
  $ready = $false
  while ((Get-Date) -lt $deadline) {
    Start-Sleep -Seconds 2
    try {
      $r = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:$NextPort/" `
            -Headers @{ Host = "localhost:$NextPort" } -TimeoutSec 3 -ErrorAction Stop
      if ($r.StatusCode -eq 200) { $ready = $true; break }
    } catch { }
  }
  if (-not $ready) { throw "Next.js server did not become healthy within 60s" }
  Write-Host "[smoke] Servers ready.`n" -ForegroundColor Green
}

function Stop-Servers {
  if ($script:mockJob) { Stop-Job $script:mockJob -ErrorAction SilentlyContinue; Remove-Job $script:mockJob -Force -ErrorAction SilentlyContinue }
  if ($script:nextJob) { Stop-Job $script:nextJob -ErrorAction SilentlyContinue; Remove-Job $script:nextJob -Force -ErrorAction SilentlyContinue }
  Write-Host "`n[smoke] Servers stopped." -ForegroundColor Cyan
}

# ─── Assertion helpers ───────────────────────────────────────────────────────

$pass = 0
$fail = 0

function Assert-Equal {
  param($label, $got, $expected)
  if ($got -like "*$expected*") {
    Write-Host "  [PASS] $label" -ForegroundColor Green
    $script:pass++
  } else {
    Write-Host "  [FAIL] $label`n         expected: $expected`n         got:      $got" -ForegroundColor Red
    $script:fail++
  }
}

# ─── Main ────────────────────────────────────────────────────────────────────

try {
  if (-not $SkipServerStart) { Start-Servers }

  $favHashes = @{}

  foreach ($t in $tenants) {
    $h = @{ Host = $t.Host }
    $base = "http://127.0.0.1:$NextPort"

    Write-Host "─── Tenant: $($t.Host) ──────────────────────────────" -ForegroundColor Yellow

    $landingPageResponse = Invoke-WebRequest -UseBasicParsing -Uri "$base/" -Headers $h
    $title    = [regex]::Match($landingPageResponse.Content, '<title>(.*?)</title>').Groups[1].Value
    $canon    = [regex]::Match($landingPageResponse.Content, '<link rel="canonical" href="([^"]+)"').Groups[1].Value
    $theme    = [regex]::Match($landingPageResponse.Content, 'data-theme="([^"]+)"').Groups[1].Value
    $layout   = [regex]::Match($landingPageResponse.Content, 'data-layout="([^"]+)"').Groups[1].Value
    $robots   = (Invoke-WebRequest -UseBasicParsing -Uri "$base/robots.txt"  -Headers $h).Content
    $sitemap  = (Invoke-WebRequest -UseBasicParsing -Uri "$base/sitemap.xml" -Headers $h).Content
    $sitemapU = [regex]::Match($sitemap, '<loc>(.*?)</loc>').Groups[1].Value

    $favFile = Join-Path $env:TEMP ("fav_" + ($t.Host -replace '[:\.]','_') + ".ico")
    Invoke-WebRequest -UseBasicParsing -Uri "$base/favicon.ico" -Headers $h -OutFile $favFile
    $favHash = (Get-FileHash $favFile -Algorithm SHA256).Hash
    $favHashes[$t.Host] = $favHash

    Assert-Equal "Title contains brand"   $title     $t.ExpTitle
    Assert-Equal "Canonical URL"          $canon     $t.ExpCanonical
    Assert-Equal "data-theme"             $theme     $t.ExpTheme
    Assert-Equal "data-layout"            $layout    $t.ExpLayout
    Assert-Equal "Robots sitemap URL"     $robots    $t.ExpSitemapUrl
    Assert-Equal "Sitemap first <loc>"    $sitemapU  $t.ExpSitemapUrl

    Write-Host "  [INFO] FaviconHash: $favHash"
    Write-Host ""
  }

  # Favicon isolation check
  $hashes = $favHashes.Values | Sort-Object -Unique
  if ($hashes.Count -eq $favHashes.Count) {
    Write-Host "  [PASS] Favicons are unique per tenant" -ForegroundColor Green
    $pass++
  } else {
    Write-Host "  [FAIL] Favicons are NOT unique — tenants share the same icon" -ForegroundColor Red
    $fail++
  }

} finally {
  if (-not $SkipServerStart) { Stop-Servers }
}

# ─── Summary ─────────────────────────────────────────────────────────────────

Write-Host "`n══════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Smoke Test Results: $pass passed, $fail failed" -ForegroundColor $(if ($fail -eq 0) { "Green" } else { "Red" })
Write-Host "══════════════════════════════════════════════`n" -ForegroundColor Cyan

if ($fail -gt 0) { exit 1 }
exit 0
