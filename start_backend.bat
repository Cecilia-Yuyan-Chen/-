@echo off
echo ========================================
echo 启动后端服务器（局域网模式）
echo ========================================
echo.
echo 服务器将在 http://0.0.0.0:8000 启动
echo 局域网内其他设备可以通过您的IP地址访问
echo.
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
pause
