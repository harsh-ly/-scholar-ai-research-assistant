@echo off
echo ============================================================
echo   Scholar AI - Serving Frontend
echo ============================================================
cd /d "%~dp0frontend"

set PYTHON_CMD=python
if exist "..\backend\venv\Scripts\python.exe" set PYTHON_CMD="..\backend\venv\Scripts\python.exe"

echo Starting server on http://127.0.0.1:5500...
echo (Note: The Flask backend also serves the frontend directly at http://127.0.0.1:5000)
echo.
start http://127.0.0.1:5500
%PYTHON_CMD% -m http.server 5500 --bind 127.0.0.1

pause

