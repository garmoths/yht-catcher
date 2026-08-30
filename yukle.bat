@echo off
setlocal
cd /d "%~dp0"

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0yukle.ps1"
if errorlevel 1 (
    echo.
    echo Kurulum basarisiz oldu. Yukaridaki hata mesajini kontrol edin.
    pause
    exit /b 1
)

echo.
pause
