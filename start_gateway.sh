#!/bin/bash

# 启动 IBKR Dashboard (Local Server)
# 无需 Notion，纯本地模式

# 杀死旧进程
pkill -f "python3 server.py"
pkill -f "python3 -m http.server"

echo "=================================================="
echo "   🚀 Starting Local Investment Dashboard"
echo "=================================================="
echo ""
echo "👉 Opening http://localhost:8085"
echo ""

# 启动自定义 Server
# 它会提供 Web 页面，并监听 /api/refresh 以触发更新
nohup python3 server.py > server.log 2>&1 &

# 等待几秒
sleep 2

echo "✅ Server is running in background."
echo "   View logs: cat server.log"
echo "=================================================="
