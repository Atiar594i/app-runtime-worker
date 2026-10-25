@echo off
title Telegram Account ^& Session Receiver Bot
color 0A
cd /d "%~dp0"

echo ======================================================
echo    Telegram Account ^& Session Receiver Bot (Local Host)
echo ======================================================
echo.

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python is not found in PATH!
    echo Please make sure Python is installed and added to PATH.
    pause
    exit /b
)

echo [*] Checking dependencies...
pip install -r requirements.txt --quiet

echo [*] Starting bot polling...
python main.py

echo.
echo [!] Bot process stopped.
pause
