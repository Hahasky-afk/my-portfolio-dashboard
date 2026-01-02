"""
Vercel Serverless Function: Portfolio Auto Update
这个函数会被Vercel Cron Job定时调用，自动更新投资组合数据
"""
import json
import os
from datetime import datetime
from http.server import BaseHTTPRequestHandler

# 延迟导入
try:
    import yfinance as yf
    import pandas as pd
    HAS_YF = True
except ImportError:
    HAS_YF = False

# 持仓配置 (硬编码以便在Vercel环境运行)
TOTAL_CASH = 0.00
POSITIONS = [
    {"symbol": "TSLA", "quantity": 881,  "cost_basis": 220.50}, 
    {"symbol": "NVDA", "quantity": 628,  "cost_basis": 45.30},
    {"symbol": "QQQM", "quantity": 414,  "cost_basis": 180.00},
    {"symbol": "META", "quantity": 30,   "cost_basis": 330.00},
    {"symbol": "AMZN", "quantity": 50,   "cost_basis": 145.00},
    {"symbol": "PLTR", "quantity": 50,   "cost_basis": 25.00},
    {"symbol": "TSM",  "quantity": 200,  "cost_basis": 0.00},
    {"symbol": "QQQ",  "quantity": 30,   "cost_basis": 0.00},
    {"symbol": "IBKR", "quantity": 64,   "cost_basis": 0.00},
]


def generate_data():
    """生成投资组合数据快照"""
    if not HAS_YF:
        return {"error": "yfinance not available"}
    
    symbols = [p["symbol"] for p in POSITIONS]
    
    # 获取实时报价
    try:
        hist = yf.download(symbols, period="5d", progress=False, group_by='ticker')
    except Exception as e:
        return {"error": f"Failed to fetch data: {str(e)}"}
    
    positions_data = []
    total_value = TOTAL_CASH
    total_day_pnl = 0.0
    total_cost = 0.0
    
    for pos in POSITIONS:
        symbol = pos["symbol"]
        qty = pos["quantity"]
        cost = pos["cost_basis"]
        
        try:
            if len(symbols) == 1:
                close_col = hist['Close']
            else:
                close_col = hist[symbol]['Close']
            
            current_price = float(close_col.dropna().iloc[-1])
            prev_close = float(close_col.dropna().iloc[-2]) if len(close_col.dropna()) > 1 else current_price
        except:
            continue
        
        market_value = current_price * qty
        day_pnl = (current_price - prev_close) * qty
        pnl_pct = ((current_price - cost) / cost * 100) if cost > 0 else 0.0
        
        total_value += market_value
        total_day_pnl += day_pnl
        total_cost += cost * qty
        
        positions_data.append({
            "symbol": symbol,
            "quantity": qty,
            "cost_basis": cost,
            "current_price": current_price,
            "market_value": market_value,
            "pnl_percent": pnl_pct,
            "day_pnl": day_pnl,
            "allocation_percent": 0  # 稍后计算
        })
    
    # 计算配置比例
    for p in positions_data:
        p["allocation_percent"] = (p["market_value"] / total_value * 100) if total_value > 0 else 0
    
    # 按市值排序
    positions_data.sort(key=lambda x: x["market_value"], reverse=True)
    
    total_pnl_val = total_value - total_cost - TOTAL_CASH
    total_pnl_pct = (total_pnl_val / total_cost * 100) if total_cost > 0 else 0.0
    
    return {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "portfolio": {
            "total_value": total_value,
            "cash": TOTAL_CASH,
            "day_pnl": total_day_pnl,
            "day_pnl_pct": (total_day_pnl / (total_value - total_day_pnl) * 100) if total_value > total_day_pnl else 0,
            "total_pnl_val": total_pnl_val,
            "total_pnl_pct": total_pnl_pct
        },
        "positions": positions_data
    }


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        data = generate_data()
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        self.wfile.write(json.dumps(data, indent=2).encode())
        return
