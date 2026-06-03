@echo off
setlocal
cd /d %~dp0
if not exist venv (
    echo Virtual environment not found. Please run setup first.
    pause
    exit /b
)
echo Activating virtual environment...
call venv\Scripts\activate.bat
echo Starting TradingAgents...
python -m cli.main
pause
