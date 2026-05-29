#!/usr/bin/env pwsh
# ForgeBase 一鍵部署腳本 — 從本機 SSH 到 Linode 執行完整部署
$ErrorActionPreference = "Stop"
$SSHHost = "root@172.234.81.223"
$SSHKeyPath = "$env:USERPROFILE\.ssh\id_rsa_linode"

function Step($msg) { Write-Host "`n>>> $msg" -ForegroundColor Cyan }

function Invoke-RemoteScript($Script, $Label) {
        # PowerShell's pipe forces CRLF when writing to external stdin.
        # Use Process directly and set NewLine=LF to avoid garbled refspecs/options.
        $Script = ($Script -replace "`r`n", "`n" -replace "`r", "`n").TrimStart("`n") + "`n"

        $psi = [System.Diagnostics.ProcessStartInfo]::new("ssh")
        $psi.Arguments  = "-i `"$SSHKeyPath`" $SSHHost `"bash -s`""
        $psi.UseShellExecute        = $false
        $psi.RedirectStandardInput  = $true
        $psi.RedirectStandardOutput = $true
        $psi.RedirectStandardError  = $true

        $proc = [System.Diagnostics.Process]::new()
        $proc.StartInfo = $psi
        $proc.Start() | Out-Null

        $proc.StandardInput.NewLine = "`n"   # force LF
        $proc.StandardInput.Write($Script)
        $proc.StandardInput.Close()

        $stdout = $proc.StandardOutput.ReadToEnd()
        $stderr = $proc.StandardError.ReadToEnd()
        $proc.WaitForExit()

        $combined = (@($stdout, $stderr) | Where-Object { $_ }) -join ""
        if ($combined) { Write-Host $combined }

        if ($proc.ExitCode -ne 0) {
                Write-Host "`n=== DEPLOY FAILED: $Label ===" -ForegroundColor Red
                exit 1
        }

        return $stdout
}

function Assert-RemoteHttp200($Url, $Label) {
    $cmd = @"
set -euo pipefail
status=`$(curl -s -o /dev/null -w '%{http_code}' '$Url')
if [ "`$status" != "200" ]; then
  echo "$Label failed with HTTP `$status" >&2
  exit 1
fi
"@

        Invoke-RemoteScript $cmd $Label | Out-Null
}

function Invoke-RemoteFrontendBuild($AppPath, $ServiceName, $Label) {
    $cmd = @(
        'set -euo pipefail',
        '',
        'install_node_deps() {',
        '    if [ -f package-lock.json ]; then',
        '        npm ci --prefer-offline 2>&1 | tail -20 || npm install --prefer-offline 2>&1 | tail -20',
        '    else',
        '        npm install --prefer-offline 2>&1 | tail -20',
        '    fi',
        '}',
        '',
        'repair_runtime_permissions() {',
        '    local service_name="$1"',
        '    local app_path="$2"',
        '    local service_user',
        '    local service_group',
        '',
        '    service_user="$(systemctl show -p User --value "$service_name")"',
        '    if [ -z "$service_user" ]; then',
        '        service_user=root',
        '    fi',
        '',
        '    service_group="$(id -gn "$service_user")"',
        '    install -d -m 755 -o "$service_user" -g "$service_group" "$app_path/.next/standalone/.next/cache"',
        '    chown "$service_user:$service_group" "$app_path/.next/standalone"',
        '    chown "$service_user:$service_group" "$app_path/.next/standalone/.next"',
        '    chown "$service_user:$service_group" "$app_path/.next/standalone/.next/cache"',
        '}',
        '',
        'cd __APP_PATH__',
        'install_node_deps',
        'npm run build 2>&1 | tail -20',
        'repair_runtime_permissions __SERVICE_NAME__ __APP_PATH__'
    ) -join "`n"
    $cmd = $cmd.Replace("__APP_PATH__", $AppPath).Replace("__SERVICE_NAME__", $ServiceName)

        Step $Label
        Invoke-RemoteScript $cmd $Label | Out-Null
}

# 0. 先 push 到 GitHub
Step "Pushing to GitHub..."
git push origin main
if ($LASTEXITCODE -ne 0) { Write-Host "git push failed" -ForegroundColor Red; exit 1 }

# 1. Pull code on server
Step "Pulling latest code on server..."
Invoke-RemoteScript @"
set -euo pipefail
cd /opt/forgebase/app
git checkout -- .
git pull --ff-only origin main
"@ "Pull latest code on server" | Out-Null

# 1b. Ensure web/public/demo symlink exists (must survive git pull)
Step "Ensuring web/public/demo asset symlink..."
Invoke-RemoteScript @"
set -euo pipefail
mkdir -p /opt/forgebase/app/web/public
# Remove stale file/dir if any; recreate as absolute symlink
if [ ! -L /opt/forgebase/app/web/public/demo ]; then
  rm -rf /opt/forgebase/app/web/public/demo
  ln -s /opt/forgebase/app/demo /opt/forgebase/app/web/public/demo
fi
ls -la /opt/forgebase/app/web/public/demo
"@ "Ensure web/public/demo asset symlink" | Out-Null

# 2. API: deps + migrations + restart
Step "Updating API (deps + migrations + restart)..."
Invoke-RemoteScript @"
set -euo pipefail
cd /opt/forgebase/app/api
source .venv/bin/activate
pip install -r requirements.txt --quiet
alembic upgrade head
systemctl restart forgebase-api
sleep 2
systemctl is-active forgebase-api
"@ "Update API (deps + migrations + restart)" | Out-Null

# 3. Admin: build + restart
Invoke-RemoteFrontendBuild "/opt/forgebase/app/admin" "forgebase-admin" "Building admin frontend..."

# 4. Web: build + restart
Invoke-RemoteFrontendBuild "/opt/forgebase/app/web" "forgebase-web" "Building web frontend..."

# 5. Restart frontends
Step "Restarting frontend services..."
Invoke-RemoteScript @"
set -euo pipefail
systemctl restart forgebase-web forgebase-admin
sleep 5
systemctl is-active forgebase-api forgebase-web forgebase-admin
"@ "Restart frontend services" | Out-Null

# 5b. Re-verify symlink (Next.js build may have wiped public/)
Step "Re-verifying web/public/demo symlink after build..."
Invoke-RemoteScript @"
set -euo pipefail
mkdir -p /opt/forgebase/app/web/public
if [ ! -L /opt/forgebase/app/web/public/demo ]; then
  rm -rf /opt/forgebase/app/web/public/demo
  ln -s /opt/forgebase/app/demo /opt/forgebase/app/web/public/demo
  echo 'Symlink recreated after build'
fi
"@ "Re-verify web/public/demo symlink" | Out-Null

Step "Runtime permission checks..."
Invoke-RemoteScript @'
set -euo pipefail

assert_runtime_permissions() {
    local service_name="$1"
    local app_path="$2"
    local service_user
    local service_group
    local actual_owner

    service_user="$(systemctl show -p User --value "$service_name")"
    if [ -z "$service_user" ]; then
        service_user=root
    fi

    service_group="$(id -gn "$service_user")"
    actual_owner="$(stat -c '%U:%G' "$app_path/.next/standalone/.next/cache")"
    if [ "$actual_owner" != "$service_user:$service_group" ]; then
        echo "$service_name cache owner mismatch: $actual_owner" >&2
        exit 1
    fi

    stat -c '%U:%G %A %n' "$app_path/.next/standalone/.next" "$app_path/.next/standalone/.next/cache"
}

assert_runtime_permissions forgebase-web /opt/forgebase/app/web
assert_runtime_permissions forgebase-admin /opt/forgebase/app/admin
'@ "Verify runtime permissions" | Out-Null

# 6. Health check
Step "Health check..."
$health = Invoke-RemoteScript @"
set -euo pipefail
curl -sf https://mitselect.com/health
"@ "Health check"
Write-Host $health
if ($health -match '"ok"') {
    Step "Critical asset checks..."
    Assert-RemoteHttp200 "https://mitselect.com/demo/handtool-company/assets/cert-iso-9001-badge.png?v=20260318a" "Certification asset"
    Assert-RemoteHttp200 "https://mitselect.com/demo/handtool-company/assets/generated/category-torque-socket-tools-hero.png?v=2" "Generated demo asset"
    Write-Host "`n=== DEPLOY SUCCESS ===" -ForegroundColor Green
} else {
    Write-Host "`n=== DEPLOY MIGHT HAVE ISSUES — check services ===" -ForegroundColor Yellow
}
