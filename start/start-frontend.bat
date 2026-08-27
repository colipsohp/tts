@echo off
REM 一键启动前端（Vite dev server，端口 5173，代理 /api 到后端 8000）
cd /d "%~dp0..\frontend"

echo ============================================
echo  启动 TTS 前端  http://localhost:5173
echo  请先启动后端：start-backend.bat
echo ============================================

if not exist "node_modules" (
    echo 首次运行，安装依赖...
    call npm install
)

call npm run dev
pause
