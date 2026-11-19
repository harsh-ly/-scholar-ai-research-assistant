# Scholar AI — PowerShell Launcher
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Scholar AI — Starting Backend Server (PowerShell)" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

Set-Location "$PSScriptRoot\backend"

if (-not (Test-Path ".env")) {
    Write-Host "Creating .env from template..." -ForegroundColor Yellow
    Copy-Item .env.example .env
}

if (-not (Test-Path "venv\Scripts\python.exe")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv venv
    Write-Host "Installing dependencies..." -ForegroundColor Yellow
    & ".\venv\Scripts\pip.exe" install -r requirements.txt --prefer-binary
}

Write-Host "Starting Flask server on http://127.0.0.1:5000..." -ForegroundColor Green
Write-Host "Access Scholar AI directly at: http://127.0.0.1:5000" -ForegroundColor Green
& ".\venv\Scripts\python.exe" run.py

