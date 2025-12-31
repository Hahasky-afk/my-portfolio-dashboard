document.addEventListener('DOMContentLoaded', () => {
    fetchData(); // 初始加载

    // 自动触发更新
    setupRefreshButton();

    // 每一分钟自动刷新一次
    setInterval(fetchData, 60000);
});

// 全局数据缓存
window.chartHistory = [];

async function fetchData() {
    const status = document.getElementById('update-status');
    const refreshBtn = document.getElementById('refresh-btn');
    if (status) status.textContent = "Updating...";
    if (refreshBtn) refreshBtn.classList.add('spinning');

    try {
        let snapshot, history;
        let isDemo = false;
        let isApi = false;

        // 1. 优先尝试 Vercel Serverless API (实时数据)
        try {
            // 添加时间戳防止缓存
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 8000); // 8秒超时

            const res = await fetch('/api/index?t=' + Date.now(), { signal: controller.signal });
            clearTimeout(timeoutId);

            if (res.ok) {
                const json = await res.json();
                if (json.data && json.history) {
                    snapshot = json.data;
                    history = json.history;
                    isApi = true;
                    console.log("Loaded data from Serverless API");
                }
            }
        } catch (e) {
            console.log("API fetch failed/timeout, falling back to static files.");
        }

        // 2. 如果 API 失败，回退到静态文件 (本地开发或 API 故障时)
        if (!snapshot) {
            try {
                const [dataRes, historyRes] = await Promise.all([
                    fetch('data.json?t=' + Date.now()),
                    fetch('history.json?t=' + Date.now())
                ]);

                if (dataRes.ok && historyRes.ok) {
                    snapshot = await dataRes.json();
                    history = await historyRes.json();
                    console.log("Loaded data from Static Files");
                } else {
                    throw new Error("Missing static data");
                }
            } catch (staticErr) {
                // 3. 最后回退到 Mock 数据
                console.warn("Loading real data failed, using mock.");
                isDemo = true;
                const [mockDataRes, mockHistoryRes] = await Promise.all([
                    fetch('mock_data.json'),
                    fetch('mock_history.json')
                ]);
                snapshot = await mockDataRes.json();
                history = await mockHistoryRes.json();
                showDemoBadge();
            }
        }

        // 渲染数据
        if (snapshot && history) {
            updateKPIs(snapshot);
            updateTable(snapshot.positions);
            updateAllocationChart(snapshot.positions);

            // 缓存并更新图表
            window.chartHistory = history;
            filterChartHistory(); // 使用缓存更新图表

            // 更新时间标签
            const timeLabel = document.getElementById('update-time');
            if (timeLabel) {
                timeLabel.textContent = `Last updated: ${snapshot.updated_at || new Date().toLocaleTimeString()}`;
                if (isDemo) timeLabel.textContent += " (DEMO)";
                if (isApi) timeLabel.textContent += " (LIVE)";
            }

            if (status) {
                status.textContent = "Updated";
                setTimeout(() => { status.textContent = ""; }, 2000);
            }
        }

    } catch (e) {
        console.error("Critical error fetching data:", e);
        if (status) status.textContent = "Error";
    } finally {
        if (refreshBtn) refreshBtn.classList.remove('spinning');
    }
}

// 刷新功能现在只是重新调用 fetchData
function refreshData() {
    fetchData();
}

function setupRefreshButton() {
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

// ---------------------------------------------------------
// UI Update Functions (Most kept same, charts updated to use window.chartHistory)
// ---------------------------------------------------------

let allocationChart = null;
let trendChart = null;
let currentTimeRange = 30;

function setupTimeSelector() {
    const buttons = document.querySelectorAll('.time-btn');
    buttons.forEach(btn => {
        btn.addEventListener('click', () => {
            buttons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentTimeRange = parseInt(btn.dataset.days);
            filterChartHistory(); // 从内存过滤，不重新请求
        });
    });
}
setupTimeSelector();

function filterChartHistory() {
    if (!window.chartHistory || window.chartHistory.length === 0) return;

    try {
        const now = new Date();
        const cutoff = new Date(now.getTime() - currentTimeRange * 24 * 60 * 60 * 1000);

        // 简单日期过滤
        const filtered = window.chartHistory.filter(h => {
            const d = new Date(h.date);
            return d >= cutoff;
        });

        updateTrendChart(filtered.length > 0 ? filtered : window.chartHistory);
    } catch (e) {
        console.error('Filter error:', e);
    }
}

function showDemoBadge() {
    let badge = document.getElementById('demo-badge');
    if (!badge) {
        badge = document.createElement('div');
        badge.id = 'demo-badge';
        badge.innerText = 'DEMO MODE';
        badge.style.cssText = 'position:fixed; bottom:20px; right:20px; background:#e82127; color:white; padding:5px 10px; border-radius:4px; font-size:12px; font-weight:bold; box-shadow:0 2px 10px rgba(0,0,0,0.3); z-index:9999;';
        document.body.appendChild(badge);
    }
}

function formatCurrency(num) {
    if (num === undefined || num === null) return "$0.00";
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(num);
}

function getStockColor(symbol) {
    const fixedColors = {
        'TSLA': '#E31937', 'NVDA': '#76B900', 'IBKR': '#B71C1C',
        'QQQ': '#F7931A', 'QQQM': '#F7931A', 'SPY': '#2962FF',
        'AAPL': '#A2AAAD', 'MSFT': '#00A4EF', 'GOOGL': '#4285F4',
        'AMZN': '#FF9900', 'META': '#0668E1'
    };
    if (fixedColors[symbol]) return fixedColors[symbol];
    const palette = ['#2979FF', '#FF9100', '#00E676', '#651FFF', '#FF1744', '#00B0FF', '#F50057', '#76FF03', '#FFC400', '#D500F9', '#1DE9B6', '#FF3D00'];
    let hash = 0;
    for (let i = 0; i < symbol.length; i++) hash = symbol.charCodeAt(i) + ((hash << 5) - hash);
    return palette[Math.abs(hash) % palette.length];
}

function updateKPIs(data) {
    const pf = data.portfolio;
    document.getElementById('total-value').textContent = formatCurrency(pf.total_value);

    const pnlEl = document.getElementById('total-pnl');
    const dayPnl = pf.day_pnl || 0;
    const dayPct = pf.day_pnl_pct || 0;

    // Day P&L
    const sign = dayPnl >= 0 ? '+' : '';
    pnlEl.textContent = `${sign}${formatCurrency(dayPnl)} (${sign}${dayPct.toFixed(2)}%)`;
    pnlEl.className = `value ${dayPnl >= 0 ? 'positive' : 'negative'}`;

    document.getElementById('cash-value').textContent = formatCurrency(pf.cash);
}

function updateTable(positions) {
    const tbody = document.getElementById('holdings-body');
    if (!tbody) return;

    tbody.innerHTML = positions.map(p => {
        // 显示日盈亏金额和百分比
        const dayPnl = p.day_pnl || 0;
        const dayPct = p.day_pnl_percent || 0;
        const pnlClass = dayPnl >= 0 ? 'positive' : 'negative';
        const sign = dayPnl >= 0 ? '+' : '';

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
                <td class="${pnlClass}">
                    <div style="font-weight:500">${sign}${formatCurrency(dayPnl)}</div>
                    <div style="font-size:11px; opacity:0.8">${sign}${dayPct.toFixed(2)}%</div>
                </td>
                <td>
                    <div style="font-weight:600">${formatCurrency(p.market_value)}</div>
                    <div style="font-size:11px; color:${(p.total_pnl || 0) >= 0 ? '#00E676' : '#FF1744'}">
                        ${(p.total_pnl || 0) >= 0 ? '+' : ''}${formatCurrency(p.total_pnl || 0)} (${(p.pnl_percent || 0).toFixed(2)}%)
                    </div>
                </td>
            </tr>
        `;
    }).join('');

    // 应用集中度检查
    const totalVal = positions.reduce((acc, p) => acc + p.market_value, 0);
    const warnings = checkConcentration(positions, totalVal);
    applyConcentrationWarnings(warnings);
}

function updateAllocationChart(positions) {
    const ctx = document.getElementById('allocationChart');
    if (!ctx) return;

    const total = positions.reduce((acc, p) => acc + p.market_value, 0);
    const labels = positions.map(p => `${p.symbol} (${((p.market_value / total) * 100).toFixed(1)}%)`);
    const data = positions.map(p => p.market_value);
    const colors = positions.map(p => getStockColor(p.symbol));
    const isMobile = window.innerWidth < 768;

    if (allocationChart) {
        allocationChart.data.labels = labels;
        allocationChart.data.datasets[0].data = data;
        allocationChart.data.datasets[0].backgroundColor = colors;
        allocationChart.update();
    } else {
        allocationChart = new Chart(ctx.getContext('2d'), {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: data,
                    backgroundColor: colors,
                    borderWidth: 0,
                    hoverOffset: 10
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '65%',
                plugins: {
                    legend: {
                        position: isMobile ? 'bottom' : 'right',
                        labels: { color: '#a0a0a0', font: { family: "'Inter', sans-serif", size: 12 }, padding: 15, boxWidth: 12, usePointStyle: true }
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
                                return ` ${context.label}: $${val.toLocaleString()} (${(val / total * 100).toFixed(1)}%)`;
                            }
                        }
                    }
                },
                layout: { padding: 10 }
            }
        });
    }
}

function updateTrendChart(history) {
    const ctx = document.getElementById('trendChart');
    if (!ctx) return;

    if (!history || history.length === 0) return;

    const dates = history.map(h => h.date);
    const values = history.map(h => h.value);
    const isUp = values[values.length - 1] >= values[0];

    const colorTheme = isUp ? {
        line: '#00E676', start: 'rgba(0, 230, 118, 0.4)', end: 'rgba(0, 230, 118, 0.0)'
    } : {
        line: '#FF1744', start: 'rgba(255, 23, 68, 0.4)', end: 'rgba(255, 23, 68, 0.0)'
    };

    const canvasCtx = ctx.getContext('2d');
    const gradient = canvasCtx.createLinearGradient(0, 0, 0, 400);
    gradient.addColorStop(0, colorTheme.start);
    gradient.addColorStop(1, colorTheme.end);

    if (trendChart) {
        trendChart.data.labels = dates;
        trendChart.data.datasets[0].data = values;
        trendChart.data.datasets[0].borderColor = colorTheme.line;
        trendChart.data.datasets[0].backgroundColor = gradient;
        trendChart.update();
    } else {
        trendChart = new Chart(canvasCtx, {
            type: 'line',
            data: {
                labels: dates,
                datasets: [{
                    label: 'Portfolio Value',
                    data: values,
                    borderColor: colorTheme.line,
                    backgroundColor: gradient,
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4,
                    pointRadius: 0,
                    pointHoverRadius: 6,
                    pointBackgroundColor: '#fff',
                    pointBorderColor: colorTheme.line
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: { mode: 'index', intersect: false },
                scales: {
                    y: {
                        position: 'right',
                        grid: { color: '#333', borderDash: [5, 5], drawBorder: false },
                        ticks: { color: '#666', callback: (v) => '$' + (v / 1000).toFixed(0) + 'k' }
                    },
                    x: {
                        grid: { display: false },
                        ticks: { color: '#666', maxTicksLimit: 6, maxRotation: 0 }
                    }
                },
                plugins: { legend: { display: false }, tooltip: { backgroundColor: 'rgba(0,0,0,0.8)', displayColors: false, callbacks: { label: (ctx) => formatCurrency(ctx.raw) } } }
            }
        });
    }
}

function updateMarketStatus() {
    const statusEl = document.getElementById('market-status');
    if (!statusEl) return;
    const now = new Date();
    const options = { timeZone: 'America/New_York', hour: 'numeric', minute: 'numeric', hour12: false };
    const etTime = new Intl.DateTimeFormat('en-US', options).format(now);
    const [hour, minute] = etTime.split(':').map(Number);
    const totalMinutes = hour * 60 + minute;
    const dayOfWeek = new Intl.DateTimeFormat('en-US', { timeZone: 'America/New_York', weekday: 'short' }).format(now);

    let status = 'closed', emoji = '⚪', text = 'Closed';
    if (dayOfWeek !== 'Sat' && dayOfWeek !== 'Sun') {
        if (totalMinutes >= 240 && totalMinutes < 570) { status = 'pre-market'; emoji = '🟡'; text = 'Pre-Market'; }
        else if (totalMinutes >= 570 && totalMinutes < 960) { status = 'trading'; emoji = '🟢'; text = 'Trading'; }
        else if (totalMinutes >= 960 && totalMinutes < 1200) { status = 'after-hours'; emoji = '🟠'; text = 'After-Hours'; }
    }
    statusEl.textContent = emoji + ' ' + text;
    statusEl.className = 'market-status ' + status;
}
updateMarketStatus();
setInterval(updateMarketStatus, 60000);

function checkConcentration(holdings, totalValue) {
    return holdings.filter(h => (h.market_value / totalValue) > 0.30).map(h => ({ symbol: h.symbol }));
}

function applyConcentrationWarnings(warnings) {
    document.querySelectorAll('.concentration-warning').forEach(e => e.remove());
    document.querySelectorAll('tbody tr').forEach(row => {
        row.classList.remove('high-concentration');
        const symbolText = row.querySelector('.symbol-cell').textContent.trim().split('\n')[1] || row.querySelector('.symbol-cell').textContent.trim();
        // 简化匹配逻辑，只看文本包含
        warnings.forEach(w => {
            if (row.innerHTML.includes(w.symbol)) {
                row.classList.add('high-concentration');
                const cell = row.querySelector('.symbol-cell');
                if (!cell.querySelector('.concentration-warning')) {
                    const span = document.createElement('span');
                    span.className = 'concentration-warning';
                    span.textContent = ' ⚠️';
                    span.title = 'High Concentration Risk (>30%)';
                    cell.querySelector('.symbol-icon').after(span);
                }
            }
        });
    });
}

// Pull to refresh support
let touchStartY = 0;
let isPulling = false;
document.addEventListener('touchstart', e => { if (window.scrollY === 0) touchStartY = e.touches[0].clientY; }, { passive: true });
document.addEventListener('touchmove', e => { if (window.scrollY === 0 && e.touches[0].clientY > touchStartY + 60) { isPulling = true; document.body.classList.add('ptr-pulling'); } }, { passive: true });
document.addEventListener('touchend', () => { if (isPulling) { isPulling = false; document.body.classList.remove('ptr-pulling'); refreshData(); } });
