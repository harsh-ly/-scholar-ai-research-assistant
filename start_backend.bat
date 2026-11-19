@echo off
echo ============================================================
echo   Scholar AI - Starting Backend Server
echo ============================================================
cd /d "%~dp0backend"

if not exist .env (
    echo Creating .env from template...
    copy .env.example .env
    echo.
    echo IMPORTANT: Edit backend\.env and add your GEMINI_API_KEY
    echo.
)

if not exist "venv\Scripts\python.exe" (
    echo Creating virtual environment...
    python -m venv venv 2>nul || py -3 -m venv venv
    if not exist "venv\Scripts\python.exe" (
        echo [ERROR] Python not found to create venv! Please install Python 3.10+ and add to PATH.
        pause
        exit /b 1
    )
    echo Installing dependencies (this may take a minute on first run)...
    call "venv\Scripts\pip.exe" install -r requirements.txt --prefer-binary
)

echo Starting Flask server on http://127.0.0.1:5000...
echo Access Scholar AI directly at: http://127.0.0.1:5000
echo.
"venv\Scripts\python.exe" run.py

pause

