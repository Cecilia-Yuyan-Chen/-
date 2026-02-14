@echo off
echo ========================================
echo 启动前端开发服务器（局域网模式）
echo ========================================
echo.
echo 服务器将在 http://0.0.0.0:3000 启动
echo 局域网内其他设备可以通过您的IP地址访问
echo.
cd frontend
npm run dev
pause
