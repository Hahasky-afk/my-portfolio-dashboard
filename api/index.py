from http.server import BaseHTTPRequestHandler
import json
import sys
import os

# 将根目录加入路径以便导入# 确保能导入根目录的模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Vercel Environment Config
os.environ['YFINANCE_CACHE_DIR'] = '/tmp/yfinance'
os.environ['MPLCONFIGDIR'] = '/tmp/matplotlib'


try:
    import main
except ImportError:
    # 尝试另一层级的引用
    sys.path.append(os.path.join(os.getcwd(), '..'))
    try:
        import main
    except ImportError:
        pass

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            # 动态重新加载以获取最新数据（虽然 Serverless 每次可能都是新的）
            import importlib
            import main
            importlib.reload(main)
            
            # 生成数据
            # result 结构: {"data": snapshot, "history": history_list}
            result = main.generate_snapshot_data()
            
            if "error" in result:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(json.dumps(result).encode('utf-8'))
                return

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*') # 允许跨域（本地调试用）
            self.end_headers()
            self.wfile.write(json.dumps(result).encode('utf-8'))
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {"error": str(e), "location": sys.path}
            self.wfile.write(json.dumps(response).encode('utf-8'))
