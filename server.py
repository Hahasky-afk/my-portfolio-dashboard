import http.server
import socketserver
import subprocess
import os
import json
import sys

# 配置
PORT = 8085
DIRECTORY = "dashboard"

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        # 设置静态文件目录
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def do_GET(self):
        # API: 手动触发数据更新
        if self.path == '/api/refresh':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            try:
                print("收到刷新请求，正在更新数据...")
                # 调用 main.py 进行更新
                # server.py 和 main.py 在同一目录
                result = subprocess.run(
                    [sys.executable, "main.py"], 
                    capture_output=True, 
                    text=True,
                    cwd=os.getcwd() 
                )
                
                if result.returncode == 0:
                    response = {"status": "success", "message": "数据已更新", "logs": result.stdout}
                else:
                    response = {"status": "error", "message": "更新失败", "logs": result.stderr}
                    
            except Exception as e:
                response = {"status": "error", "message": str(e)}
            
            self.wfile.write(json.dumps(response).encode())
            return

        # 默认处理：提供静态文件
        super().do_GET()

if __name__ == "__main__":
    # 确保 dashboard 目录存在
    if not os.path.exists(DIRECTORY):
        print(f"Error: Directory '{DIRECTORY}' not found.")
        sys.exit(1)
        
    # 允许地址重用
    socketserver.TCPServer.allow_reuse_address = True
    
    # 绑定到 0.0.0.0 以允许局域网访问
    with socketserver.TCPServer(("0.0.0.0", PORT), Handler) as httpd:
        # 获取本机 IP 用于提示
        try:
            import socket
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            # 尝试获取真实的局域网 IP (针对 Mac/Linux)
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
        except:
            local_ip = "YOUR_IP_ADDRESS"

        print(f"✅ 服务已启动!")
        print(f"   💻 电脑访问: http://localhost:{PORT}")
        print(f"   📱 手机访问: http://{local_ip}:{PORT} (需连同一Wi-Fi)")
        print(f"📂 静态目录: {DIRECTORY}")
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n🛑 服务已停止")
