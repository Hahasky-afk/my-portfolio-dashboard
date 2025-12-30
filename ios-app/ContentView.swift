import SwiftUI

// --- 数据模型 ---

struct PortfolioResponse: Codable {
    let portfolio: Portfolio
    let positions: [Position]
    let updated_at: String
}

struct Portfolio: Codable {
    let total_value: Double
    let day_pnl: Double
    let day_pnl_pct: Double
    let total_pnl_val: Double
    let total_pnl_pct: Double
    let cash: Double
}

struct Position: Codable, Identifiable {
    var id: String { symbol }
    let symbol: String
    let quantity: Double
    let current_price: Double
    let market_value: Double
    let pnl_percent: Double
    let day_pnl: Double
    let allocation_percent: Double
}

// --- 主视图 ---

struct ContentView: View {
    @State private var data: PortfolioResponse?
    @State private var isLoading = false
    @State private var errorMessage: String?
    
    // ⚠️ 注意：这里填入刚才获取的局域网 IP
    // 如果在模拟器运行，可以使用 localhost
    // 如果在真机运行，必须使用电脑的局域网 IP (例如 192.168.6.172)
    let serverURL = "http://192.168.6.172:8085/data.json"
    let refreshURL = "http://192.168.6.172:8085/api/refresh"
    
    var body: some View {
        NavigationView {
            ScrollView {
                if let data = data {
                    VStack(spacing: 20) {
                        // 1. 顶部 KPI 卡片
                        HeaderCard(portfolio: data.portfolio)
                        
                        // 2. 持仓列表
                        VStack(alignment: .leading) {
                            Text("Positions")
                                .font(.headline)
                                .padding(.horizontal)
                            
                            ForEach(data.positions) { position in
                                PositionRow(position: position)
                            }
                        }
                    }
                    .padding(.vertical)
                } else if isLoading {
                    ProgressView("Loading Portfolio...")
                        .padding(.top, 50)
                } else if let error = errorMessage {
                    VStack {
                        Image(systemName: "exclamationmark.triangle")
                            .font(.largeTitle)
                            .foregroundColor(.orange)
                        Text(error)
                            .multilineTextAlignment(.center)
                            .padding()
                        Button("Retry") { fetchData() }
                    }
                    .padding(.top, 50)
                }
            }
            .navigationTitle("Investment")
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button(action: triggerRefresh) {
                        Image(systemName: "arrow.clockwise")
                    }
                }
            }
        }
        .onAppear { fetchData() }
        .refreshable {
            await triggerRefreshAsync()
        }
    }
    
    func fetchData() {
        isLoading = true
        guard let url = URL(string: serverURL) else { return }
        
        URLSession.shared.dataTask(with: url) { d, _, err in
            DispatchQueue.main.async {
                isLoading = false
                if let err = err {
                    self.errorMessage = "Connection Failed: \(err.localizedDescription)\nMake sure Mac is running and on same WiFi."
                    return
                }
                guard let d = d else { return }
                do {
                    self.data = try JSONDecoder().decode(PortfolioResponse.self, from: d)
                    self.errorMessage = nil
                } catch {
                    self.errorMessage = "Data Error: \(error.localizedDescription)"
                }
            }
        }.resume()
    }
    
    func triggerRefresh() {
        guard let url = URL(string: refreshURL) else { return }
        URLSession.shared.dataTask(with: url).resume()
        // Wait a bit then reload
        DispatchQueue.main.asyncAfter(deadline: .now() + 2) {
            fetchData()
        }
    }
    
    func triggerRefreshAsync() async {
        triggerRefresh()
        try? await Task.sleep(nanoseconds: 2 * 1_000_000_000)
    }
}

// --- 子视图组件 ---

struct HeaderCard: View {
    let portfolio: Portfolio
    
    var body: some View {
        VStack(spacing: 15) {
            VStack(spacing: 5) {
                Text("Total Portfolio Value")
                    .font(.subheadline)
                    .foregroundColor(.secondary)
                Text(formatCurrency(portfolio.total_value))
                    .font(.system(size: 36, weight: .bold))
                    .foregroundColor(.primary)
            }
            
            HStack(spacing: 40) {
                KPIItem(
                    label: "Day P&L",
                    value: portfolio.day_pnl,
                    pct: portfolio.day_pnl_pct
                )
                
                KPIItem(
                    label: "Total P&L",
                    value: portfolio.total_pnl_val,
                    pct: portfolio.total_pnl_pct
                )
            }
        }
        .padding(20)
        .background(Color(UIColor.secondarySystemBackground))
        .cornerRadius(16)
        .padding(.horizontal)
    }
}

struct KPIItem: View {
    let label: String
    let value: Double
    let pct: Double
    
    var color: Color { value >= 0 ? .green : .red }
    var sign: String { value >= 0 ? "+" : "" }
    
    var body: some View {
        VStack(spacing: 5) {
            Text(label).font(.caption).foregroundColor(.secondary)
            Text("\(sign)\(formatCurrency(value))")
                .font(.headline)
                .foregroundColor(color)
            Text("\(sign)\(String(format: "%.2f", pct))%")
                .font(.caption)
                .fontWeight(.bold)
                .foregroundColor(color)
                .padding(.horizontal, 6)
                .padding(.vertical, 2)
                .background(color.opacity(0.1))
                .cornerRadius(4)
        }
    }
}

struct PositionRow: View {
    let position: Position
    let colors: [String: Color] = [
        "TSLA": .red, "NVDA": .green, "AAPL": .gray,
        "MSFT": .blue, "AMZN": .orange, "GOOG": .blue, "META": .blue
    ]
    
    var body: some View {
        HStack {
            // Icon
            ZStack {
                Circle()
                    .fill(colors[position.symbol] ?? Color.gray)
                    .opacity(0.1)
                    .frame(width: 40, height: 40)
                Text(String(position.symbol.prefix(1)))
                    .fontWeight(.bold)
                    .foregroundColor(colors[position.symbol] ?? Color.primary)
            }
            
            VStack(alignment: .leading) {
                Text(position.symbol)
                    .font(.headline)
                Text("\(Int(position.quantity)) shares")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
            
            Spacer()
            
            VStack(alignment: .trailing) {
                Text(formatCurrency(position.market_value))
                    .fontWeight(.medium)
                
                HStack(spacing: 4) {
                    Text(position.day_pnl >= 0 ? "+" : "") +
                    Text(String(format: "%.2f%%", position.pnl_percent))
                }
                .font(.caption)
                .foregroundColor(position.pnl_percent >= 0 ? .green : .red)
            }
        }
        .padding()
        .background(Color(UIColor.systemBackground))
        .cornerRadius(10)
        .padding(.horizontal)
    }
}

// --- 工具函数 ---

func formatCurrency(_ value: Double) -> String {
    let formatter = NumberFormatter()
    formatter.numberStyle = .currency
    formatter.currencyCode = "USD"
    formatter.maximumFractionDigits = 0
    return formatter.string(from: NSNumber(value: value)) ?? "$0"
}

// --- 预览 ---
struct ContentView_Previews: PreviewProvider {
    static var previews: some View {
        ContentView()
            .preferredColorScheme(.dark) // 默认深色模式
    }
}
