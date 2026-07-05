@echo off
chcp 65001 >nul 2>&1
title xkw-watermark-cleaner - Web Build
cd /d "D:\My Program\xkw-watermark-cleaner-main\body_web"

echo ================================================================
echo   xkw-watermark-cleaner - Web Build (Vite + React + Express)
echo ================================================================
echo.

REM --- Detect Node.js / npm ---
where npm >nul 2>&1
if %errorlevel% equ 0 goto :node_found

if exist "C:\Program Files\nodejs\npm.cmd" set "PATH=C:\Program Files\nodejs;%PATH%" && goto :node_found

if exist "%LOCALAPPDATA%\Programs\nodejs\npm.cmd" set "PATH=%LOCALAPPDATA%\Programs\nodejs;%PATH%" && goto :node_found

if exist "C:\Users\Com-DESKTOP-9N69UEQ\.workbuddy\binaries\node\versions\22.22.2\npm.cmd" set "PATH=C:\Users\Com-DESKTOP-9N69UEQ\.workbuddy\binaries\node\versions\22.22.2;%PATH%" && goto :node_found

echo.
echo [ERROR] Node.js / npm not found!
echo Please install Node.js LTS from https://nodejs.org/
echo.
pause
exit /b 1

:node_found
echo [OK] Node detected
echo.

echo ------------------------------------------------
echo  Step 1/5: Installing frontend dependencies...
echo ------------------------------------------------
cd frontend
call npm install --cache "..\.npm-cache"
if errorlevel 1 goto :error_fe_install
cd ..
echo [OK] Frontend deps installed
echo.

echo ------------------------------------------------
echo  Step 2/5: Building frontend (Vite)...
echo ------------------------------------------------
cd frontend
call npm run build
if errorlevel 1 goto :error_fe_build
cd ..
echo [OK] Frontend built
echo.

echo ------------------------------------------------
echo  Step 3/5: Installing backend dependencies...
echo ------------------------------------------------
cd backend
call npm install --cache "..\.npm-cache"
if errorlevel 1 goto :error_be_install
echo [OK] Backend deps installed
echo.

echo ------------------------------------------------
echo  Step 4/5: Building backend (TypeScript)...
echo ------------------------------------------------
call npm run build
if errorlevel 1 goto :error_be_build
cd ..
echo [OK] Backend built
echo.

echo ------------------------------------------------
echo  Step 5/5: Packaging zip...
echo ------------------------------------------------
"D:\My Program\Python\python.exe" scripts\package_zip.py
echo.

echo ================================================================
echo   Build complete!
echo   Frontend: frontend\dist\
echo   Backend:  backend\dist\
echo   To start: start_web.bat
echo   URL:      http://localhost:3001
echo ================================================================
echo.
pause
exit /b 0

:error_fe_install
echo [ERROR] Frontend npm install failed!
pause
exit /b 1

:error_fe_build
echo [ERROR] Frontend build failed!
pause
exit /b 1

:error_be_install
echo [ERROR] Backend npm install failed!
pause
exit /b 1

:error_be_build
echo [ERROR] Backend build failed!
pause
exit /b 1
