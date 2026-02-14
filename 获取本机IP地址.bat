@echo off
echo 正在获取本机IP地址...
echo.
ipconfig | findstr /i "IPv4"
echo.
echo 请使用上述IP地址访问游戏
echo 例如: http://192.168.x.x:3000
pause
