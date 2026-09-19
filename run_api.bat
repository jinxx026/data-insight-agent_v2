@echo off
setlocal

cd /d "%~dp0"

set API_URL=http://127.0.0.1:8000/docs

if not exist ".venv\Scripts\python.exe" (
    echo Creating local virtual environment...
    py -3 -m venv .venv
    if errorlevel 1 (
        python -m venv .venv
    )
    if not exist ".venv\Scripts\python.exe" (
        echo Failed to create .venv. Please install Python 3 and try again.
        pause
        exit /b 1
    )
)

".venv\Scripts\python.exe" -c "import fastapi, uvicorn, multipart, pandas, openpyxl, requests, pyarrow, sqlalchemy, pymysql, email_validator" >nul 2>nul
if errorlevel 1 (
    echo Installing project dependencies...
    ".venv\Scripts\python.exe" -m pip install -r requirements-api.txt
    if errorlevel 1 (
        echo Failed to install dependencies.
        pause
        exit /b 1
    )
)

echo Starting DataInsight Agent API...
echo.
echo The API docs should open automatically.
echo If they do not, open:
echo %API_URL%
echo.
echo Keep this window open while using the API.
echo Press Ctrl+C to stop the server.
echo.

start "" cmd /c "timeout /t 5 /nobreak >nul && start "" %API_URL%"

".venv\Scripts\python.exe" -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

pause
