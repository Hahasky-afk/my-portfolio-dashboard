# 📈 Local Investment Dashboard

这是一个私有的、本地运行的投资组合仪表盘。
它不依赖 IBKR API 的复杂配置，而是采用 **"手动持仓配置 + 自动实时计价"** 的混合模式，既安全又灵活。

## ✨ 主要功能

*   **全家桶视图**：汇总你自己、家人等多个账户的持仓。
*   **实时计价**：通过 `yfinance` 自动获取股票最新价格，计算总市值 (Total Market Value)。
*   **实时 P&L**：自动计算今日盈亏 (Day P&L) 和累计盈亏。
*   **历史回溯**：基于当前持仓，自动回溯过去 30 天的资产净值曲线，展示真实的波动趋势。
*   **本地安全**：所有数据仅保存在本地 JSON 文件中，不上传任何服务器（Notion 同步已移除）。

## 🚀 快速开始

### 1. 启动 Dashboard (只需一次)
在终端中运行 Web 服务器：
```bash
./start_gateway.sh
```
或者手动运行：
```bash
python3 -m http.server 8085 --directory dashboard
```
然后浏览器访问：[http://localhost:8085](http://localhost:8085)

## ☁️ 进阶：云端部署 (电脑关机也能看)

如果你希望随时随地查看，且不用一直开着电脑，可以使用 **GitHub + Vercel** (完全免费 + 私有)。

1.  **上传代码**：将本项目上传到 GitHub 创建一个 **Private (私有)** 仓库。
2.  **自动更新**：项目里已经内置了 `.github/workflows/update.yml`，它会在美股交易时段**每小时自动运行**，更新股价。
3.  **连接 Vercel**：
    *   去 [vercel.com](https://vercel.com) 注册个账号。
    *   点击 "Add New Project"，选择导入你刚才的 GitHub 仓库。
    *   **Root Directory** (根目录) 选择 `dashboard`。
    *   点击 Deploy。
4.  **完成**：Vercel 会给你一个网址 (如 `https://my-portfolio.vercel.app`)，这就是你的永久专属 App 链接！

### 2. 更新数据 (日常操作)
想刷新最新股价或更新了持仓后，运行：
```bash
./update.sh
```
或者：
```bash
python3 main.py
```

## ⚙️ 如何修改持仓

所有持仓数据都存储在 `manual_portfolio.py` 文件中。

1.  打开 `manual_portfolio.py`。
2.  找到 `POSITIONS` 列表。
3.  按格式修改或添加股票：
    ```python
    {"symbol": "NVDA", "quantity": 100, "cost_basis": 45.30},
    ```
    *   `symbol`: 股票代码 (如 TSLA, BTC-USD)
    *   `quantity`: 持股数量 (卖出/做空用负数)
    *   `cost_basis`: 单股平均成本 (用于计算累计回报，不影响总市值)
4.  保存文件。
5.  运行 `./update.sh` 即可生效。

## 🛠️ 文件结构

*   `manual_portfolio.py`: **[核心]** 你的持仓配置文件。
*   `main.py`: **[引擎]** 负责读取配置、抓取 Yahoo 价格、生成数据。
*   `dashboard/`: **[前端]** 包含 HTML/CSS/JS 网页文件。
*   `update.sh`: 一键更新脚本。
*   `start_gateway.sh`: 启动 Web 服务器脚本。

## ⚠️ 注意事项

*   **现金 (Cash)**: 在 `manual_portfolio.py` 中修改 `TOTAL_CASH` 变量来调整现金余额。
*   **期权/复杂标的**: 如果 Yahoo 搜不到代码，可以在条目中增加 `"manual_price": 1.5` 来手动指定价格。
Last deployment trigger: Wed Dec 31 10:19:02 CST 2025
