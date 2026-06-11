@echo off
setlocal
cd /d %~dp0
if not exist venv (
    echo Virtual environment not found. Creating one now...
    python -m venv venv
    if errorlevel 1 (
        echo Failed to create virtual environment. Please install Python 3.10+ and try again.
        pause
        exit /b
    )
)
echo Activating virtual environment...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo Failed to activate virtual environment.
    pause
    exit /b
)
python -m pip --version >nul 2>&1
if errorlevel 1 (
    echo Pip not found in virtual environment. Installing pip...
    python -m ensurepip --upgrade
    if errorlevel 1 (
        echo Failed to install pip. Delete the venv folder and run start.bat again.
        pause
        exit /b
    )
)
echo Installing/updating dependencies...
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo Failed to install dependencies.
    pause
    exit /b
)
echo Starting TradingAgents...
python -m cli.main --checkpoint
pause
