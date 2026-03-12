@echo off
title Slay the Spire 2 - Painter

:: Change to script directory
cd /d "%~dp0"

echo ========================================
echo    Slay the Spire 2 - Digital Amber Painter
echo ========================================
echo.
echo Starting program...
echo.

:: Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [Error] Python not detected, please install Python first!
    echo Download: https://www.python.org/downloads/
    pause
    exit /b 1
)

:: Check dependencies
echo Checking dependencies...
python -c "import cv2, PIL, keyboard, numpy" >nul 2>&1
if errorlevel 1 (
    echo [Info] Missing dependencies, installing...
    python -m pip install opencv-python Pillow keyboard numpy
    if errorlevel 1 (
        echo [Error] Failed to install dependencies!
        pause
        exit /b 1
    )
)

echo [Success] Dependencies OK!
echo.
echo Starting painter...
echo.

:: Start program
python spire_painter.py

echo.
echo Press any key to close...
pause >nul
