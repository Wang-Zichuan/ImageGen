@echo off
chcp 65001 >nul
echo ==============================
echo   ImageGen 环境配置
echo ==============================
echo.

where uv >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未检测到 uv，请先安装: https://docs.astral.sh/uv/getting-started/installation/
    pause
    exit /b 1
)

if not exist config.json (
    copy config.example.json config.json
    echo [提示] 已创建 config.json，请编辑填入你的 API Key
)

echo [1/2] 安装依赖...
uv sync
if %errorlevel% neq 0 (
    echo [错误] 依赖安装失败
    pause
    exit /b 1
)

echo.
echo [2/2] 验证安装...
uv run python -c "import streamlit, openai, PIL; print('依赖验证通过')" 2>nul
if %errorlevel% neq 0 (
    echo [错误] 依赖验证失败
    pause
    exit /b 1
)

echo.
echo ==============================
echo   配置完成！
echo   运行 start.bat 启动应用
echo ==============================
pause