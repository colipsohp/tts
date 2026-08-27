@echo off
REM 一键启动后端（FastAPI + uvicorn，端口 8000）
cd /d "%~dp0..\backend"

echo ============================================
echo  启动 TTS 后端服务  http://127.0.0.1:8000
echo  文档  http://127.0.0.1:8000/docs
echo ============================================

REM 首次运行自动安装依赖
if not exist ".venv\Scripts\python.exe" (
    echo 首次运行，安装依赖...
    uv sync
)

".venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000
pause
