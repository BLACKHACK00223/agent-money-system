# Script de verification de l'installation QZ Tray (site KONE)
$ErrorActionPreference = "SilentlyContinue"
$ok = $true

Write-Host "=== VERIFICATION QZ TRAY (kone-service.saheltech.tech) ===" -ForegroundColor Cyan
Write-Host ""

# 1. QZ Tray installe ?
$qzExe = @("C:\Program Files\QZ Tray\qz-tray.exe", "C:\Program Files (x86)\QZ Tray\qz-tray.exe") | Where-Object { Test-Path $_ } | Select-Object -First 1
if ($qzExe) {
    $ver = (Get-Item $qzExe).VersionInfo.FileVersion
    Write-Host "[OK] QZ Tray trouve : $qzExe (version $ver)" -ForegroundColor Green
    $v2 = [version]$ver
    if ($v2.Major -lt 2 -or ($v2.Major -eq 2 -and $v2.Minor -lt 1)) {
        Write-Host "[!!] Version < 2.1 : override.crt ne sera pas lu. Mettez a jour QZ Tray (https://qz.io/download/)" -ForegroundColor Yellow
    }
} else {
    Write-Host "[KO] QZ Tray NON installe. Telechargez-le sur https://qz.io/download/ et installez-le" -ForegroundColor Red
    $ok = $false
}

# 2. override.crt present ?
$qlDir = Split-Path $qzExe -Parent
$override = Join-Path $qlDir "override.crt"
if (Test-Path $override) {
    Write-Host "[OK] override.crt present : $override" -ForegroundColor Green
    if (Test-Path "$PSScriptRoot\digital-certificate.txt") {
        $a = (Get-FileHash $override).Hash
        $b = (Get-FileHash "$PSScriptRoot\digital-certificate.txt").Hash
        if ($a -eq $b) {
            Write-Host "[OK] override.crt = identique au certificat KONE du dossier" -ForegroundColor Green
        } else {
            Write-Host "[!!] override.crt DIFFERENT du certificat KONE du dossier (fichier perime ?)" -ForegroundColor Yellow
        }
    }
} else {
    Write-Host "[KO] override.crt ABSENT. Lancez installer.bat en administrateur ou copiez digital-certificate.txt vers $override" -ForegroundColor Red
    $ok = $false
}

# 3. QZ Tray en cours d'execution ?
$proc = Get-Process -Name "qz-tray" -ErrorAction SilentlyContinue
if ($proc) {
    Write-Host "[OK] QZ Tray en cours d'execution (pid $($proc.Id))" -ForegroundColor Green
} else {
    Write-Host "[KO] QZ Tray n'est PAS lance. Lancez-le (menu Demarrer -> QZ Tray)" -ForegroundColor Red
    $ok = $false
}

# 4. allowed.dat (une fois coche "Remember")
$allowed = Join-Path $env:APPDATA "qz\allowed.dat"
if (Test-Path $allowed) {
    Write-Host "[OK] allowed.dat existe (deja approuve une fois)" -ForegroundColor Green
} else {
    Write-Host "[..] allowed.dat pas encore cree (normal avant la 1ere impression)" -ForegroundColor Yellow
}

# 5. Reachability du site
try {
    $r = Invoke-WebRequest -Uri "https://kone-service.saheltech.tech/sign-message?request=test" -UseBasicParsing -TimeoutSec 10
    if ($r.StatusCode -eq 200 -and $r.Content.Length -gt 64) {
        Write-Host "[OK] Le site repond : /sign-message renvoie une signature valide ($($r.Content.Length) chars)" -ForegroundColor Green
    } else {
        Write-Host "[!!] /sign-message repond $($r.StatusCode) mais contenu inattendu : $($r.Content)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "[KO] Impossible d'atteindre https://kone-service.saheltech.tech/sign-message : $($_.Exception.Message)" -ForegroundColor Red
    $ok = $false
}

Write-Host ""
if ($ok) {
    Write-Host "=== TOUT EST EN ORDRE : l'impression doit fonctionner sans popup ===" -ForegroundColor Green
} else {
    Write-Host "=== IL RESTE DES PROBLEMES A CORRIGER (voir messages [KO] ci-dessus) ===" -ForegroundColor Red
}
Read-Host "Appuyez sur Entree pour fermer"