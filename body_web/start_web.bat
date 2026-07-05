@echo off
chcp 65001 >nul 2>&1
title xkw-watermark-cleaner - Web Server
cd /d "D:\My Program\xkw-watermark-cleaner-main\body_web\backend"

REM --- Detect Node.js / npm ---
where npm >nul 2>&1
if %errorlevel% equ 0 goto :node_found

if exist "C:\Program Files\nodejs\npm.cmd" set "PATH=C:\Program Files\nodejs;%PATH%" && goto :node_found

if exist "%LOCALAPPDATA%\Programs\nodejs\npm.cmd" set "PATH=%LOCALAPPDATA%\Programs\nodejs;%PATH%" && goto :node_found

if exist "C:\Users\Com-DESKTOP-9N69UEQ\.workbuddy\binaries\node\versions\22.22.2\npm.cmd" set "PATH=C:\Users\Com-DESKTOP-9N69UEQ\.workbuddy\binaries\node\versions\22.22.2;%PATH%" && goto :node_found

echo [ERROR] Node.js / npm not found!
echo Please install Node.js LTS from https://nodejs.org/
pause
exit /b 1

:node_found
echo ================================================================
echo   xkw-watermark-cleaner - Web Server
echo   http://localhost:3001
echo ================================================================
echo Press Ctrl+C to stop.
echo.

npm start

pause
