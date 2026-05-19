@echo off
chcp 65001 >nul
echo ==============================
echo   ImageGen Setup
echo ==============================
echo.

where uv >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] uv not found. Install it first: https://docs.astral.sh/uv/getting-started/installation/
    pause
    exit /b 1
)

if not exist config.json (
    copy config.example.json config.json
    echo [TIP] config.json created. Please edit it and fill in your API Key.
)

echo [1/2] Installing dependencies...
uv sync
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)

echo.
echo [2/2] Verifying installation...
uv run python -c "import streamlit, openai, PIL; print('All dependencies OK')" 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Dependency verification failed.
    pause
    exit /b 1
)

echo.
echo ==============================
echo   Setup complete!
echo   Run start.bat to launch the app
echo ==============================
pause