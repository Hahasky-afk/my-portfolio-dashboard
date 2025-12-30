# 手动持仓配置
# 基于用户截图 (2025-12-30) 更新
# 包含用户本人及家人的总持仓汇总

# 现金 (维持之前的负余额配置)
TOTAL_CASH = 0.00

# 持仓列表
POSITIONS = [
    # --- 已知成本的持仓 (沿用之前数据或预估) ---
    {"symbol": "TSLA", "quantity": 881,  "cost_basis": 220.50}, 
    {"symbol": "NVDA", "quantity": 628,  "cost_basis": 45.30},
    {"symbol": "QQQM", "quantity": 414,  "cost_basis": 180.00},
    {"symbol": "META", "quantity": 30,   "cost_basis": 330.00},
    {"symbol": "AMZN", "quantity": 50,   "cost_basis": 145.00},
    {"symbol": "PLTR", "quantity": 50,   "cost_basis": 25.00},
    
    # --- 新增/其他账号持仓 (截图新增, 成本暂未知, 设为0) ---
    {"symbol": "TSM",  "quantity": 200,  "cost_basis": 0.00},
    {"symbol": "QQQ",  "quantity": 30,   "cost_basis": 0.00}, # 注意区分 QQQ 和 QQQM
    {"symbol": "IBKR", "quantity": 64,   "cost_basis": 0.00},
    
    # 注意: 截图里没有 SPY, 这里移除 SPY
    # 注意: 截图里没有 期权, 这里移除期权
]
