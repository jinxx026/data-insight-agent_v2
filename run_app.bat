@echo off
setlocal

cd /d "%~dp0"

set APP_PORT=8501
netstat -ano | findstr /R /C:":8501 .*LISTENING" >nul 2>nul
if not errorlevel 1 (
    set APP_PORT=8502
)
netstat -ano | findstr /R /C:":8502 .*LISTENING" >nul 2>nul
if not errorlevel 1 (
    set APP_PORT=8503
)
set APP_URL=http://127.0.0.1:%APP_PORT%
set STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
set STREAMLIT_SERVER_HEADLESS=true
set STREAMLIT_CLIENT_TOOLBAR_MODE=minimal

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

".venv\Scripts\python.exe" -c "import streamlit, pandas, openpyxl, altair, requests, pyarrow" >nul 2>nul
if errorlevel 1 (
    echo Installing project dependencies...
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo Failed to install dependencies.
        pause
        exit /b 1
    )
)

echo Starting DataInsight Agent...
echo.
echo The browser should open automatically.
echo If it does not, open:
echo %APP_URL%
echo.
echo Keep this window open while using the app.
echo Press Ctrl+C to stop the server.
echo.

start "" cmd /c "timeout /t 5 /nobreak >nul && start "" %APP_URL%"

".venv\Scripts\python.exe" -m streamlit run "frontend\streamlit_app.py" --server.headless=true --browser.gatherUsageStats=false --server.address=127.0.0.1 --server.port=%APP_PORT%

pause
