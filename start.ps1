$PSScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $PSScriptRoot

if (-not (Test-Path "venv")) {
    Write-Host "Virtual environment not found. Please run setup first." -ForegroundColor Red
    pause
    exit
}

Write-Host "Activating virtual environment..." -ForegroundColor Cyan
. .\venv\Scripts\Activate.ps1

Write-Host "Starting TradingAgents..." -ForegroundColor Green
python -m cli.main
pause
