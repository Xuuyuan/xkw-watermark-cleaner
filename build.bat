@echo off
chcp 65001 >nul 2>&1
title xkw-watermark-cleaner - Build
cd /d "D:\My Program\xkw-watermark-cleaner-main"

echo ================================================================
echo   xkw-watermark-cleaner - Build All
echo   Standalone + Lite + Online
echo ================================================================
echo.
echo Python: D:\My Program\Python\python.exe
echo Project: %CD%
echo.
echo ------------------------------------------------
echo  Step 1/3: Cleaning old build cache...
echo ------------------------------------------------
if exist "build" rmdir /s /q "build"
if exist "__pycache__" rmdir /s /q "__pycache__"

echo.
echo ------------------------------------------------
echo  Step 2/3: Building Standalone + Lite...
echo ------------------------------------------------
"D:\My Program\Python\python.exe" build_all.py

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Build failed! Check the log above.
    echo.
    pause
    exit /b 1
)

echo.
echo ================================================================
echo   Build complete!
echo   - Standalone: dist\独立版\学科网水印清理工具_独立版.exe
echo   - Lite:      dist\精简版\学科网水印清理工具_精简版.exe
echo   - Online:    dist\在线版\学科网水印清理工具_在线版.zip
echo ================================================================
echo.
pause
