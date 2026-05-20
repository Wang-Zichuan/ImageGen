@echo off
chcp 65001 >nul
echo ==============================
echo   ImageGen Setup
echo ==============================
echo.

where uv >nul 2>&1
if %errorlevel% neq 0 (
    echo [TIP] uv not found. Installing uv...
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to install uv. Please install manually: https://docs.astral.sh/uv/getting-started/installation/
        pause
        exit /b 1
    )
    echo [OK] uv installed successfully.
    echo.
)

if not exist config.json (
    copy config.example.json config.json
    echo [TIP] config.json created. Please edit it and fill in your API Key.
)

echo [1/3] Installing dependencies...
uv sync
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)

echo.
echo [2/3] Installing project package...
uv pip install -e .
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install project package.
    pause
    exit /b 1
)

echo.
echo [3/3] Verifying installation...
uv run python -c "import imagegen; import streamlit, openai, PIL; print('All dependencies OK')" 2>nul
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