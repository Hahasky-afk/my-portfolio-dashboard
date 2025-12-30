document.addEventListener('DOMContentLoaded', () => {
    fetchData();
    // 初始加载现有数据
    fetchData();

    // 自动触发更新
    refreshData();

    // 每一分钟刷新一次视图 (不触发后端更新，只读 JSON)
    setInterval(fetchData, 60000);

    setupRefreshButton();
});

// 新增：触发后端更新
async function refreshData() {
    const btn = document.getElementById('refresh-btn');
    const status = document.getElementById('update-status');

    if (btn) {
        btn.disabled = true;
        btn.classList.add('spinning');
    }
    if (status) status.textContent = "Updating prices...";

    try {
        const res = await fetch('/api/refresh');
        const data = await res.json();

        if (data.status === 'success') {
            console.log("Update success:", data.message);
            fetchData(); // 重新加载最新数据
            if (status) status.textContent = "Updates received";
            setTimeout(() => { if (status) status.textContent = ""; }, 3000);
        } else {
            console.error("Update failed:", data.message);
            if (status) status.textContent = "Update failed";
        }
    } catch (e) {
        console.warn("Auto-refresh skipped (Backend not running?)");
        if (status) status.textContent = "";
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.classList.remove('spinning');
        }
    }
}

let allocationChart = null;
let trendChart = null;

async function fetchData() {
    try {
        // 尝试加载真实数据
        let data, history;
        let isDemo = false;

        try {
            const [dataRes, historyRes] = await Promise.all([
                fetch('data.json?t=' + Date.now()),
                fetch('history.json?t=' + Date.now())
            ]);

            if (!dataRes.ok || !historyRes.ok) throw new Error("Missing real data");

            data = await dataRes.json();
            history = await historyRes.json();
        } catch (realDataError) {
            console.warn("Loading real data failed.", realDataError);
            isDemo = true;
            // 如果加载失败，尝试 mock
            try {
                const [mockDataRes, mockHistoryRes] = await Promise.all([
                    fetch('mock_data.json'),
                    fetch('mock_history.json')
                ]);
                data = await mockDataRes.json();
                history = await mockHistoryRes.json();
                showDemoBadge();
            } catch (e) {
                console.error("Failed to load both real and mock data");
                return;
            }
        }

        updateKPIs(data);
        updateTable(data.positions);
        updateAllocationChart(data.positions);
        updateTrendChart(history);

        const timeLabel = document.getElementById('update-time');
        if (timeLabel) {
            timeLabel.textContent = `Last updated: ${data.updated_at || new Date().toLocaleTimeString()}`;
            if (isDemo) timeLabel.textContent += " (DEMO MODE)";
        }

    } catch (e) {
        console.error("Failed to fetch data:", e);
    }
}

function setupRefreshButton() {
    // 动态添加刷新按钮到 Header
    const header = document.querySelector('header');
    if (header && !document.getElementById('refresh-btn')) {
        const div = document.createElement('div');
        div.className = 'header-actions';
        div.innerHTML = `
            <span id="update-status" style="font-size:12px; margin-right:10px; color:#888;"></span>
            <button id="refresh-btn" onclick="refreshData()" title="Refresh Prices">↻</button>
        `;
        header.appendChild(div);
    }
}

function showDemoBadge() {
    let badge = document.getElementById('demo-badge');
    if (!badge) {
        badge = document.createElement('div');
        badge.id = 'demo-badge';
        badge.innerText = 'DEMO MODE';
        badge.style.cssText = 'position:fixed; bottom:20px; right:20px; background:#e82127; color:white; padding:5px 10px; border-radius:4px; font-size:12px; font-weight:bold; box-shadow:0 2px 10px rgba(0,0,0,0.3);';
        document.body.appendChild(badge);
    }
}

function formatCurrency(num) {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(num);
}

function getStockColor(symbol) {
    // 强制指定颜色 (主要持仓)
    const fixedColors = {
        'TSLA': '#E31937', // Red
        'NVDA': '#76B900', // Green
        'IBKR': '#B71C1C'  // Dark Red
    };

    if (fixedColors[symbol]) return fixedColors[symbol];

    // 自动分配高对比度色盘 (避免相似色)
    // 调色板来源: Material Design 500/A200 + Distinct Sets
    const palette = [
        '#2979FF', // Blue A400
        '#FF9100', // Orange A400
        '#00E676', // Green A400
        '#651FFF', // Deep Purple A400
        '#FF1744', // Red A400
        '#00B0FF', // Light Blue A400
        '#F50057', // Pink A400
        '#76FF03', // Light Green A400
        '#FFC400', // Amber A400
        '#D500F9', // Purple A400
        '#1DE9B6', // Teal A400
        '#FF3D00'  // Deep Orange A400
    ];

    // 使用简单的哈希算法确保同一个 Symbol 总是分配到同一个颜色
    let hash = 0;
    for (let i = 0; i < symbol.length; i++) {
        hash = symbol.charCodeAt(i) + ((hash << 5) - hash);
    }

    return palette[Math.abs(hash) % palette.length];
}

function updateKPIs(data) {
    const pf = data.portfolio;
    document.getElementById('total-value').textContent = formatCurrency(pf.total_value);

    const pnlEl = document.getElementById('total-pnl');
    // 使用 day_pnl (今日盈亏) 替代 total_pnl (总盈亏)
    const sign = pf.day_pnl >= 0 ? '+' : '';
    pnlEl.textContent = `${sign}${formatCurrency(pf.day_pnl)} (${sign}${pf.day_pnl_pct.toFixed(2)}%)`;
    pnlEl.className = `value ${pf.day_pnl >= 0 ? 'positive' : 'negative'}`;

    document.getElementById('cash-value').textContent = formatCurrency(pf.cash);
}

function updateTable(positions) {
    const tbody = document.getElementById('holdings-body');
    tbody.innerHTML = positions.map(p => {
        const pnlClass = p.pnl_percent >= 0 ? 'positive' : 'negative';
        const sign = p.pnl_percent >= 0 ? '+' : '';
        return `
            <tr>
                <td>
                    <div class="symbol-cell">
                        <div class="symbol-icon" style="color:${getStockColor(p.symbol)}">${p.symbol[0]}</div>
                        ${p.symbol}
                    </div>
                </td>
                <td>${p.quantity}</td>
                <td>${formatCurrency(p.current_price)}</td>
                <td style="color:#a0a0a0">${(p.allocation_percent || 0).toFixed(1)}%</td>
                <td class="${pnlClass}">${sign}${p.pnl_percent.toFixed(2)}%</td>
                <td>${formatCurrency(p.market_value)}</td>
            </tr>
        `;
    }).join('');
}

function updateAllocationChart(positions) {
    const ctx = document.getElementById('allocationChart').getContext('2d');

    // 计算总市值用于计算百分比 (也可以直接用 p.allocation_percent)
    const total = positions.reduce((acc, p) => acc + p.market_value, 0);

    // 生成带百分比的标签
    const labels = positions.map(p => {
        const pct = ((p.market_value / total) * 100).toFixed(1);
        return `${p.symbol} (${pct}%)`;
    });

    const data = positions.map(p => p.market_value);
    const colors = positions.map(p => getStockColor(p.symbol));

    if (allocationChart) {
        allocationChart.data.labels = labels;
        allocationChart.data.datasets[0].data = data;
        allocationChart.data.datasets[0].backgroundColor = colors;
        allocationChart.options.plugins.legend.labels.font.size = 14; // Update font size dynamically
        allocationChart.update();
    } else {
        // 响应式配置：手机端图例在下，桌面端在右
        const isMobile = window.innerWidth < 768;

        allocationChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: data, // Corrected from 'values'
                    backgroundColor: colors, // Corrected from 'bgColors'
                    borderWidth: 0,
                    hoverOffset: 10
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '65%', // 更细的圆环
                plugins: {
                    legend: {
                        position: isMobile ? 'bottom' : 'right', // 手机端放下边
                        labels: {
                            color: '#a0a0a0',
                            font: {
                                size: 12,
                                family: "'Inter', sans-serif"
                            },
                            padding: 15,
                            boxWidth: 12,
                            usePointStyle: true
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(37, 37, 37, 0.9)',
                        titleColor: '#fff',
                        bodyColor: '#fff',
                        padding: 12,
                        cornerRadius: 8,
                        callbacks: {
                            label: function (context) {
                                const val = context.raw;
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const pct = (val / total * 100).toFixed(1) + '%';
                                return ` ${context.label}: $${val.toLocaleString()} (${pct})`;
                            }
                        }
                    }
                },
                layout: {
                    padding: {
                        top: 10,
                        bottom: 10
                    }
                }
            }
        });
    }
}

function updateTrendChart(history) {
    const ctx = document.getElementById('trendChart').getContext('2d');

    const dates = history.map(h => h.date);
    const values = history.map(h => h.value);

    // 1. 判断整体趋势 (涨/跌) 来决定颜色
    const startVal = values[0] || 0;
    const endVal = values[values.length - 1] || 0;
    const isUp = endVal >= startVal;

    // 定义颜色主题
    const colorTheme = isUp ? {
        line: '#00E676', // Bright Green
        start: 'rgba(0, 230, 118, 0.4)',
        end: 'rgba(0, 230, 118, 0.0)'
    } : {
        line: '#FF1744', // Red A400
        start: 'rgba(255, 23, 68, 0.4)',
        end: 'rgba(255, 23, 68, 0.0)'
    };

    // 2. 创建渐变填充
    const gradient = ctx.createLinearGradient(0, 0, 0, 400);
    gradient.addColorStop(0, colorTheme.start);
    gradient.addColorStop(1, colorTheme.end);

    if (trendChart) {
        // 如果图表已存在，更新数据和颜色
        trendChart.data.labels = dates;
        trendChart.data.datasets[0].data = values;
        trendChart.data.datasets[0].borderColor = colorTheme.line;
        trendChart.data.datasets[0].backgroundColor = gradient;
        trendChart.update();
    } else {
        trendChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: dates,
                datasets: [{
                    label: 'Portfolio Value',
                    data: values,
                    borderColor: colorTheme.line,
                    backgroundColor: gradient,
                    borderWidth: 2, // 线条稍微细一点更显得精致
                    fill: true,     // 开启填充
                    tension: 0.4,   // 平滑曲线
                    pointRadius: 0, // 默认隐藏数据点，更平滑
                    pointHoverRadius: 6, // 鼠标悬停时显示大点
                    pointBackgroundColor: '#fff', // 悬停点为白色
                    pointBorderColor: colorTheme.line,
                    pointBorderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'index',
                    intersect: false,
                },
                scales: {
                    y: {
                        display: true,
                        position: 'right', // y轴放右边更像专业软件
                        grid: {
                            color: '#333',
                            borderDash: [5, 5], // 虚线网格
                            drawBorder: false   // 不画y轴竖线
                        },
                        ticks: {
                            color: '#666',
                            font: { family: "'Inter', sans-serif", size: 10 },
                            callback: (v) => '$' + (v / 1000).toFixed(0) + 'k'
                        }
                    },
                    x: {
                        grid: { display: false }, // 隐藏x轴网格
                        ticks: {
                            color: '#666',
                            maxTicksLimit: 6, // 限制日期显示数量
                            maxRotation: 0,
                            font: { family: "'Inter', sans-serif", size: 10 }
                        }
                    }
                },
                plugins: {
                    legend: { display: false }, // 隐藏图例
                    tooltip: {
                        backgroundColor: 'rgba(0,0,0,0.8)',
                        titleColor: '#fff',
                        bodyColor: '#fff',
                        padding: 10,
                        displayColors: false, // 不显示颜色方块
                        callbacks: {
                            label: (ctx) => formatCurrency(ctx.raw)
                        }
                    }
                }
            }
        });
    }
}
