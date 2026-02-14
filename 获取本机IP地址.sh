#!/bin/bash
echo "正在获取本机IP地址..."
echo ""
if command -v ip &> /dev/null; then
    ip addr show | grep "inet " | grep -v 127.0.0.1
elif command -v ifconfig &> /dev/null; then
    ifconfig | grep "inet " | grep -v 127.0.0.1
fi
echo ""
echo "请使用上述IP地址访问游戏"
echo "例如: http://192.168.x.x:3000"
