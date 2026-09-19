@echo off
setlocal

cd /d "%~dp0"

set BUILDX_GIT_INFO=false
if "%PIP_INDEX_URL%"=="" (
    set PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
)

docker --version >nul 2>nul
if errorlevel 1 (
    echo Docker was not found.
    echo Please install Docker Desktop first, then run this script again.
    pause
    exit /b 1
)

echo Starting DataInsight Agent with Docker Compose...
echo.
echo Streamlit:
echo http://127.0.0.1:8501
echo.
echo FastAPI docs:
echo http://127.0.0.1:8000/docs
echo.
echo Keep this window open while using the services.
echo Press Ctrl+C to stop the services.
echo.

docker compose up --build

pause
