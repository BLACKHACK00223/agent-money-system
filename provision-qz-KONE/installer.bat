@echo off
:: ============================================================
::  KONE SERVICES - Approbation permanente QZ Tray
::  Installe override.crt pour ne plus jamais demander "Allow"
:: ============================================================
setlocal EnableDelayedExpansion
chcp 65001 >nul 2>&1

echo ==================================================
echo    QZ Tray - Approbation permanente KONE
echo ==================================================
echo.

:: 1. Le certificat doit etre present a cote de ce script
if not exist "%~dp0digital-certificate.txt" (
    echo [ERREUR] digital-certificate.txt introuvable a cote du script.
    echo           Verifiez le contenu du dossier provision-qz.
    pause
    exit /b 1
)

:: 2. Trouver le dossier d'installation de QZ Tray
set "QZ_DIR="
if exist "C:\Program Files\QZ Tray\"   set "QZ_DIR=C:\Program Files\QZ Tray"
if exist "C:\Program Files (x86)\QZ Tray\" set "QZ_DIR=C:\Program Files (x86)\QZ Tray"

if not defined QZ_DIR (
    echo [ERREUR] QZ Tray introuvable dans les dossiers standard.
    echo           Localisez son dossier : icone QZ Tray ^> Diagnostics
    echo           ^> App Folder, puis copiez digital-certificate.txt
    echo           en le renommant override.crt dedans manuellement.
    pause
    exit /b 1
)

echo [OK] Installation QZ Tray : %QZ_DIR%

:: 3. Copier le certificat comme racine de confiance
copy /Y "%~dp0digital-certificate.txt" "%QZ_DIR%\override.crt" >nul
if errorlevel 1 (
    echo [ERREUR] Impossible de copier override.crt.
    echo           Lancez ce script EN TANT QU'ADMINISTRATEUR
    echo           (clic droit ^> Executer en tant qu'administrateur).
    pause
    exit /b 1
)
echo [OK] override.crt copie.

:: 4. Verifier le contenu du certificat
findstr /C:"BEGIN CERTIFICATE" "%QZ_DIR%\override.crt" >nul 2>&1
if errorlevel 1 (
    echo [ERREUR] override.crt semble invalide.
    pause
    exit /b 1
)
echo [OK] Certificat valide.

:: 5. Redemarrer QZ Tray
echo [OK] Redemarrage de QZ Tray en cours...
taskkill /IM "qz-tray.exe" /F >nul 2>&1
timeout /t 2 /nobreak >nul
start "" "%QZ_DIR%\qz-tray.exe"

echo.
echo ==================================================
echo   TERMINE !
echo   QZ Tray ne demandera plus jamais le "Allow"
echo   pour les impressions depuis kone-service.saheltech.tech
echo ==================================================
echo.
pause
endlocal