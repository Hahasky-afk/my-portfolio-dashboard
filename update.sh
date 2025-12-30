#!/bin/bash

# 获取脚本所在目录
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo "=================================================="
echo "   IBKR Dashboard Update Utility"
echo "=================================================="

# 运行 Python 主程序
# 1. 读取 manual_portfolio.py
# 2. 从 Yahoo Finance 获取最新股价
# 3. 更新 dashboard/data.json 和 history.json
python3 main.py

echo "--------------------------------------------------"
echo "✅ 更新完成！请刷新浏览器: http://localhost:8085"
echo "=================================================="
