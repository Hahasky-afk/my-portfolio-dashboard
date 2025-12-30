"""
IBKR Local Dashboard - Core Engine
功能: 读取 manual_portfolio.py 配置，通过 yfinance 获取实时行情，生成 Dashboard 数据。
"""
import json
import os
from datetime import datetime
from collections import defaultdict
import manual_portfolio as mp

def main():
    print("=" * 50)
    print("   Portfolio Updater")
    print("=" * 50)
    
    # 1. 读取持仓配置
    positions = []
    if hasattr(mp, 'POSITIONS'):
        positions = mp.POSITIONS
    else:
        print("Error: manual_portfolio.py 中未找到 POSITIONS 配置")
        return

    # 2. 获取实时行情 (Yahoo Finance)
    print(f"\n[1/3] 获取实时行情 ({len(positions)} 个标的)...")
    try:
        import yfinance as yf
        import pandas as pd
        
        # 提取需要查询的 Symbol (排除有手动定价的)
        symbols = [p['symbol'] for p in positions if 'manual_price' not in p and ' ' not in p['symbol']]
        # 加上 SPY 作为市场基准/交易日参考
        fetch_list = list(set(symbols + ['SPY']))
        
        # 批量获取当前数据 (使用 Tickers 对象)
        tickers = yf.Tickers(' '.join(fetch_list))
        
        # 获取 Day P&L 需要的昨收价
        day_pnl_map = {}
        
        for p in positions:
            sym = p['symbol']
            
            # 默认值
            current_price = 0.0
            prev_close = 0.0
            
            # 如果有手动定价
            if 'manual_price' in p:
                current_price = float(p['manual_price'])
                # 手动定价无法自动计算日内盈亏，除非手动指定昨收，这里简单处理为0变化
                prev_close = current_price 
            else:
                # 从 Yahoo 获取
                try:
                    t = tickers.tickers[sym]
                    
                    # 尝试 fast_info
                    if hasattr(t, 'fast_info'):
                        fi = t.fast_info
                        if hasattr(fi, 'last_price'): current_price = fi.last_price
                        if hasattr(fi, 'previous_close'): prev_close = fi.previous_close
                    
                    # 回退到 info
                    if not current_price:
                        info = t.info
                        current_price = info.get('currentPrice') or info.get('regularMarketPrice')
                        if not prev_close:
                            prev_close = info.get('previousClose') or info.get('regularMarketPreviousClose')
                            
                except Exception as e:
                    print(f"  警告: 无法获取 {sym} 行情 ({e})")

            # 更新持仓数据
            if current_price:
                p['current_price'] = float(current_price)
                p['market_value'] = p['quantity'] * current_price
                
                # 计算各种盈亏
                cost = p.get('cost_basis', 0) * p['quantity']
                
                # 累计盈亏 %
                if cost != 0:
                    p['pnl_percent'] = (p['market_value'] - cost) / cost * 100
                else:
                    p['pnl_percent'] = 0.0
                
                # 今日盈亏 (Day P&L)
                if prev_close:
                    change = current_price - prev_close
                    d_pnl = change * p['quantity']
                    p['day_pnl'] = d_pnl
                    day_pnl_map[sym] = d_pnl
                    print(f"  > {sym:<5} ${current_price:>7.2f} | Day: ${d_pnl:>+8.2f}")
                else:
                    p['day_pnl'] = 0.0
                    print(f"  > {sym:<5} ${current_price:>7.2f}")
    
    except ImportError:
        print("Error: 未安装 yfinance。请运行 pip install yfinance")
        return

    # 3. 汇总组合数据
    print("\n[2/3] 计算组合总值...")
    total_market_value = sum(p.get('market_value', 0) for p in positions)
    
    # 占比
    for p in positions:
        p['allocation_percent'] = (p.get('market_value', 0) / total_market_value * 100) if total_market_value else 0

    # 现金与总资产
    cash = getattr(mp, 'TOTAL_CASH', 0.0)
    grand_total = total_market_value + cash
    
    # 汇总 Day P&L
    total_day_pnl = sum(p.get('day_pnl', 0) for p in positions)
    yesterday_val = grand_total - total_day_pnl
    day_pnl_pct = (total_day_pnl / yesterday_val * 100) if yesterday_val else 0
    
    # 汇总 Total P&L
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
    
    # 保存 data.json
    base_dir = os.path.dirname(os.path.abspath(__file__))
    dashboard_dir = os.path.join(base_dir, 'dashboard')
    os.makedirs(dashboard_dir, exist_ok=True)
    
    with open(os.path.join(dashboard_dir, 'data.json'), 'w', encoding='utf-8') as f:
        json.dump(snapshot, f, indent=2)

    # 4. 生成/更新历史数据 (Trend Chart)
    print("\n[3/3] 更新历史走势 (30 Days)...")
    update_history(positions, cash, dashboard_dir, grand_total)
    
    print("-" * 50)
    print(f"✅ 更新完成! 总资产: ${grand_total:,.2f}")

def update_history(positions, cash, out_dir, current_total):
    """基于当前持仓回溯历史数据"""
    history_file = os.path.join(out_dir, 'history.json')
    history = []
    
    try:
        import yfinance as yf
        import pandas as pd
        
        symbols = [p['symbol'] for p in positions if 'manual_price' not in p and ' ' not in p['symbol']]
        if symbols:
            # 下载过去30天数据
            data = yf.download(list(set(symbols + ['SPY'])), period="1mo", progress=False)['Close']
            
            for date, row in data.iterrows():
                daily_sum = 0.0
                for p in positions:
                    sym = p['symbol']
                    qty = p['quantity']
                    # 获取该日价格
                    price = 0.0
                    if sym in row and not pd.isna(row[sym]):
                        price = float(row[sym])
                    elif 'manual_price' in p:
                        price = float(p['manual_price'])
                    elif 'current_price' in p:
                        price = p['current_price']
                    
                    daily_sum += price * qty
                
                daily_sum += cash
                history.append({
                    "date": date.strftime("%Y-%m-%d"),
                    "value": daily_sum
                })
    except Exception as e:
        print(f"历史回溯警告: {e}")
        # 如果失败，保留旧文件或仅存今日
        if os.path.exists(history_file):
            return

    # 确保最后一条是当前最新值
    today = datetime.now().strftime("%Y-%m-%d")
    if not history:
        history.append({"date": today, "value": current_total})
    elif history[-1]['date'] == today:
        history[-1]['value'] = current_total
    else:
        history.append({"date": today, "value": current_total})
        
    with open(history_file, 'w', encoding='utf-8') as f:
        json.dump(history, f, indent=2)

if __name__ == "__main__":
    main()
