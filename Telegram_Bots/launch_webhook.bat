@echo off
REM Launch Webhook Server and ngrok for Telegram Bot

REM Change to script directory
cd /d %~dp0

REM Start webhook server in a new window
start "Webhook Server" cmd /k "python Webhooks\webhook_server.py"

REM Check if ngrok.exe exists in PATH or current directory
where ngrok >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] ngrok.exe not found in PATH. Please download from https://ngrok.com/download and add to PATH or place in this folder.
    pause
    exit /b 1
)

REM Start ngrok on port 5000 in a new window
start "ngrok" cmd /k "ngrok http 5000"

echo [INFO] Webhook server and ngrok launched. Check the new windows for logs.
pause 