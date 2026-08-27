@echo off
REM 一键启动前后端：后端 8000 + 前端 5173
cd /d "%~dp0"

echo ============================================
echo  正在启动 TTS 语音合成工具...
echo ============================================

start "TTS-Backend" cmd /k "start-backend.bat"
timeout /t 3 >nul
start "TTS-Frontend" cmd /k "start-frontend.bat"

echo.
echo 后端: http://127.0.0.1:8000  (docs: /docs)
echo 前端: http://localhost:5173
echo 关闭本窗口不影响服务（请分别关闭两个服务窗口）
timeout /t 5 >nul
