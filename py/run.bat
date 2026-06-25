@echo off
cd /d "%~dp0"
echo AI-AutoJS Python 桌面版启动中...
uv run python main.py
if errorlevel 1 (
    echo [错误] 启动失败，请确认已安装 uv 和依赖：uv sync
    pause
)
