"""
IBKR Local Dashboard - Core Engine
功能: 读取 manual_portfolio.py 配置，通过 yfinance 获取实时行情，生成 Dashboard 数据。
"""
import json
import os
from datetime import datetime
from collections import defaultdict
import manual_portfolio as mp

# 导入 yfinance (延迟导入以防环境问题)
try:
    import yfinance as yf
    import pandas as pd
    HAS_YF = True
except ImportError:
    HAS_YF = False

def generate_snapshot_data():
    """核逻辑：获取数据并返回字典对象，不进行文件写入"""
    if not HAS_YF:
        return {"error": "yfinance not installed"}

    # 1. 读取持仓配置
    positions = []
    if hasattr(mp, 'POSITIONS'):
        positions = [p.copy() for p in mp.POSITIONS] # Deep copy to avoid mutating original
    else:
        return {"error": "No POSITIONS found in manual_portfolio.py"}

    # 2. 获取实时行情 (Yahoo Finance)
    # 提取需要查询的 Symbol (排除有手动定价的)
    symbols = [p['symbol'] for p in positions if 'manual_price' not in p and ' ' not in p['symbol']]
    fetch_list = list(set(symbols + ['SPY']))
    
    # 批量获取当前数据
    tickers_dict = {}
    prev_closes = {}
    current_prices = {}
    
    if fetch_list:
        try:
            # 使用 download 获取最近5天数据，确保能拿到昨收
            # group_by='ticker' 方便处理
            hist = yf.download(fetch_list, period="5d", progress=False, group_by='ticker')
            
            # 遍历每个标的处理数据
            for sym in fetch_list:
                try:
                    # 处理单个 ticker 数据 (如果是单个标的，结构不同，需要判断)
                    df = None
                    if len(fetch_list) == 1:
                        df = hist
                    else:
                        # 检查列是否存在 (防御性编程)
                        if isinstance(hist.columns, pd.MultiIndex):
                             if sym in hist.columns.levels[0]:
                                 df = hist[sym]
                        elif sym in hist: # 兼容非MultiIndex情况
                             df = hist[sym]
                    
                    if df is None:
                        print(f"Warning: No data found for {sym} in batch result")
                        continue

                    # 移除空行
                    df = df.dropna()

                    
                    if not df.empty and len(df) >= 2:
                        # 有至少两天数据
                        current_prices[sym] = float(df['Close'].iloc[-1])
                        prev_closes[sym] = float(df['Close'].iloc[-2])
                    elif not df.empty:
                        # 只有一天数据 (IPO? 或数据缺失)
                        current_prices[sym] = float(df['Close'].iloc[-1])
                        prev_closes[sym] = float(df['Open'].iloc[-1]) # Fallback to open
                except Exception as e:
                    print(f"Error parse hist for {sym}: {e}")
                    
        except Exception as e:
            print(f"Batch download failed: {e}")

    day_pnl_map = {}
    
    for p in positions:
        sym = p['symbol']
        current_price = 0.0
        prev_close = 0.0
        
        # 手动定价优先
        if 'manual_price' in p:
            current_price = float(p['manual_price'])
            prev_close = current_price
        else:
            # 使用批量获取的数据
            current_price = current_prices.get(sym, 0.0)
            prev_close = prev_closes.get(sym, 0.0)
            
            # 如果批量失败，尝试备用方案 (fast_info) -- 仅作为最后的防线
            if current_price == 0:
                try:
                    t = yf.Ticker(sym)
                    if hasattr(t, 'fast_info'):
                        if hasattr(t.fast_info, 'last_price'): current_price = t.fast_info.last_price
                        if hasattr(t.fast_info, 'previous_close'): prev_close = t.fast_info.previous_close
                except: pass

        # 计算持仓数据
        if current_price:
            p['current_price'] = float(current_price)
            p['market_value'] = p['quantity'] * current_price
            
            cost = p.get('cost_basis', 0) * p['quantity']
            # P&L %
            if cost != 0:
                p['pnl_percent'] = (p['market_value'] - cost) / cost * 100
            else:
                p['pnl_percent'] = 0.0
            
            # Day P&L
            if prev_close:
                change = current_price - prev_close
                d_pnl = change * p['quantity']
                p['day_pnl'] = d_pnl
                p['day_pnl_percent'] = (change / prev_close) * 100
            else:
                p['day_pnl'] = 0.0
                p['day_pnl_percent'] = 0.0
        else:
            p['market_value'] = 0.0
            p['day_pnl'] = 0.0
            p['day_pnl_percent'] = 0.0

    # 3. 汇总组合数据
    total_market_value = sum(p.get('market_value', 0) for p in positions)
    
    # 占比
    for p in positions:
        p['allocation_percent'] = (p.get('market_value', 0) / total_market_value * 100) if total_market_value else 0

    cash = getattr(mp, 'TOTAL_CASH', 0.0)
    grand_total = total_market_value + cash
    
    total_day_pnl = sum(p.get('day_pnl', 0) for p in positions)
    yesterday_val = grand_total - total_day_pnl
    day_pnl_pct = (total_day_pnl / yesterday_val * 100) if yesterday_val else 0
    
    total_cost = sum(p.get('cost_basis', 0) * p['quantity'] for p in positions)
    total_pnl_val = total_market_value - total_cost
    total_pnl_pct = (total_pnl_val / total_cost * 100) if total_cost else 0
    
    snapshot = {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "portfolio": {
            "total_value": grand_total,
            "cash": cash,
            "day_pnl": total_day_pnl,
            "day_pnl_pct": day_pnl_pct,
            "total_pnl_val": total_pnl_val,
            "total_pnl_pct": total_pnl_pct
        },
        "positions": sorted(positions, key=lambda x: x['market_value'], reverse=True)
    }
    
    # 4. 同时生成历史数据
    history_data = generate_history_data(positions, cash, grand_total)
    
    return {
        "data": snapshot,
        "history": history_data
    }

def generate_history_data(positions, cash, current_total):
    """基于当前持仓回溯历史数据 (纯内存计算)"""
    history = []
    try:
        symbols = [p['symbol'] for p in positions if 'manual_price' not in p and ' ' not in p['symbol']]
        if symbols:
            # 下载过去30天数据
            data = yf.download(list(set(symbols + ['SPY'])), period="1mo", progress=False)['Close']
            
            for date, row in data.iterrows():
                daily_sum = 0.0
                for p in positions:
                    sym = p['symbol']
                    qty = p['quantity']
                    price = 0.0
                    
                    # 尝试从历史数据获取
                    try:
                        if sym in row and not pd.isna(row[sym]):
                            price = float(row[sym])
                    except: pass
                    
                    # 回退逻辑
                    if price == 0:
                        if 'manual_price' in p: price = float(p['manual_price'])
                        elif 'current_price' in p: price = p['current_price']
                        
                    daily_sum += price * qty
                
                daily_sum += cash
                history.append({
                    "date": date.strftime("%Y-%m-%d"),
                    "value": daily_sum
                })
    except Exception as e:
        print(f"History error: {e}")
        return []

    # 确保最后一条是今天
    today = datetime.now().strftime("%Y-%m-%d")
    if not history:
        history.append({"date": today, "value": current_total})
    elif history[-1]['date'] != today:
        history.append({"date": today, "value": current_total})
    else:
        history[-1]['value'] = current_total
        
    return history

def main():
    """本地运行入口: 调用逻辑并保存文件"""
    print("=" * 50)
    print("   Portfolio Updater (Local / API Ready)")
    print("=" * 50)
    
    result = generate_snapshot_data()
    
    if "error" in result:
        print(f"Error: {result['error']}")
        return

    snapshot = result['data']
    history = result['history']
    
    # 保存文件
    base_dir = os.path.dirname(os.path.abspath(__file__))
    dashboard_dir = os.path.join(base_dir, 'dashboard')
    os.makedirs(dashboard_dir, exist_ok=True)
    
    with open(os.path.join(dashboard_dir, 'data.json'), 'w', encoding='utf-8') as f:
        json.dump(snapshot, f, indent=2)
        
    with open(os.path.join(dashboard_dir, 'history.json'), 'w', encoding='utf-8') as f:
        json.dump(history, f, indent=2)
        
    print(f"[OK] Update Complete! Total: ${snapshot['portfolio']['total_value']:,.2f}")

if __name__ == "__main__":
    main()
