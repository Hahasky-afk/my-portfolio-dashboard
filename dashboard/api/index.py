"""
Vercel Serverless Function: Portfolio Real-Time API
前端调用 /api/index 获取实时投资组合数据
一劳永逸方案：每次访问都实时获取最新数据，无需定时任务
"""
from http.server import BaseHTTPRequestHandler
import json
from datetime import datetime, timedelta

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


def generate_snapshot():
    """生成投资组合快照数据"""
    if not HAS_YF:
        return None, "yfinance not available"
    
    symbols = [p["symbol"] for p in POSITIONS]
    
    try:
        hist = yf.download(symbols, period="5d", progress=False, group_by='ticker')
    except Exception as e:
        return None, f"Failed to fetch data: {str(e)}"
    
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
            
            closes = close_col.dropna()
            current_price = float(closes.iloc[-1])
            prev_close = float(closes.iloc[-2]) if len(closes) > 1 else current_price
        except:
            continue
        
        market_value = current_price * qty
        day_pnl = (current_price - prev_close) * qty
        day_pnl_pct = ((current_price - prev_close) / prev_close * 100) if prev_close > 0 else 0.0
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
            "day_pnl_percent": day_pnl_pct,
            "allocation_percent": 0
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
    }, None


def generate_history(positions, cash, current_total):
    """生成历史数据（基于当前持仓回溯）"""
    if not HAS_YF:
        return []
    
    symbols = [p["symbol"] for p in positions]
    quantities = {p["symbol"]: p["quantity"] for p in positions}
    
    try:
        end = datetime.now()
        start = end - timedelta(days=90)
        hist = yf.download(symbols, start=start.strftime("%Y-%m-%d"), end=end.strftime("%Y-%m-%d"), 
                          progress=False, group_by='ticker')
    except:
        return []
    
    history = []
    
    try:
        if len(symbols) == 1:
            dates = hist.index.tolist()
            closes = hist['Close'].tolist()
            for i, dt in enumerate(dates):
                val = closes[i] * quantities[symbols[0]] + cash
                if not pd.isna(val):
                    history.append({
                        "date": dt.strftime("%Y-%m-%d"),
                        "value": round(val, 2)
                    })
        else:
            dates = hist.index.tolist()
            for dt in dates:
                daily_val = cash
                valid = True
                for sym in symbols:
                    try:
                        price = hist[sym]['Close'].loc[dt]
                        if pd.isna(price):
                            valid = False
                            break
                        daily_val += float(price) * quantities[sym]
                    except:
                        valid = False
                        break
                if valid:
                    history.append({
                        "date": dt.strftime("%Y-%m-%d"),
                        "value": round(daily_val, 2)
                    })
    except Exception as e:
        print(f"History generation error: {e}")
    
    return history


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # 生成实时快照
        snapshot, error = generate_snapshot()
        
        if error:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"error": error}).encode())
            return
        
        # 生成历史数据
        history = generate_history(
            POSITIONS, 
            TOTAL_CASH, 
            snapshot["portfolio"]["total_value"]
        )
        
        # 返回前端期望的格式
        response = {
            "data": snapshot,
            "history": history
        }
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.end_headers()
        self.wfile.write(json.dumps(response).encode())
