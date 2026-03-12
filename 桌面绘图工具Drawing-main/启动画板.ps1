# Slay the Spire 2 - Digital Amber Painter Launcher
$Host.UI.RawUI.WindowTitle = "Slay the Spire 2 - Painter"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   Slay the Spire 2 - Digital Amber Painter" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Starting program..." -ForegroundColor Yellow
Write-Host ""

# Check Python
$pythonCheck = & python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[Error] Python not detected, please install Python first!" -ForegroundColor Red
    Write-Host "Download: https://www.python.org/downloads/" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "Python found: $pythonCheck" -ForegroundColor Green
Write-Host ""

# Check dependencies
Write-Host "Checking dependencies..." -ForegroundColor Yellow
$depCheck = & python -c "import cv2, PIL, keyboard, numpy" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[Info] Missing dependencies, installing..." -ForegroundColor Yellow
    & python -m pip install opencv-python Pillow keyboard numpy
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[Error] Failed to install dependencies!" -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
}

Write-Host "[Success] Dependencies OK!" -ForegroundColor Green
Write-Host ""
Write-Host "Starting painter..." -ForegroundColor Yellow
Write-Host ""

# Start program
& python spire_painter.py

Write-Host ""
Write-Host "Program exited. Press any key to close..." -ForegroundColor Cyan
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
