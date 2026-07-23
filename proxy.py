#!/usr/bin/env python3
"""
TYC 代理服务器 —— 解决天眼查 API 的浏览器跨域限制。
启动后访问 http://127.0.0.1:8765 即可使用前端。

启动方式: python3 proxy.py
"""

import http.server
import urllib.request
import urllib.error
import json
import ssl
import os

PROXY_PORT = int(os.environ.get('PORT', 8765))
TYC_API_BASE = "https://open.api.tianyancha.com"
STATIC_DIR = os.path.dirname(os.path.abspath(__file__))


class ProxyHandler(http.server.BaseHTTPRequestHandler):

    def do_GET(self):
        path = self.path.split('?')[0]

        if path == '/ping':
            self.send_json({"ok": True, "service": "TYC Proxy"})

        elif path.startswith('/tyc/'):
            self.proxy_request('GET')

        elif path == '/' or path == '':
            self.serve_static('app_2.html')

        else:
            self.serve_static(path.lstrip('/'))

    def do_POST(self):
        if self.path.startswith('/tyc/'):
            self.proxy_request('POST')
        else:
            self.send_response(404)
            self._cors()
            self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def proxy_request(self, method):
        api_path = self.path.replace('/tyc', '', 1)
        target_url = TYC_API_BASE + api_path
        token = self.headers.get('X-TYC-Token', '')

        body = None
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length > 0:
            body = self.rfile.read(content_length)

        req = urllib.request.Request(target_url, data=body, method=method)
        req.add_header('Authorization', token)
        req.add_header('Content-Type', 'application/json; charset=utf-8')

        ctx = ssl.create_default_context()

        try:
            with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
                data = resp.read()
                self.send_response(resp.status)
                self._cors()
                ct = resp.headers.get('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Content-Type', ct)
                self.end_headers()
                self.wfile.write(data)

        except urllib.error.HTTPError as e:
            data = e.read()
            self.send_response(e.code)
            self._cors()
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(data)

        except urllib.error.URLError as e:
            self.send_response(502)
            self._cors()
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps({
                "error": True,
                "reason": f"无法连接天眼查 API: {e.reason}",
                "tip": "请检查网络是否可访问 open.api.tianyancha.com"
            }, ensure_ascii=False).encode())

        except Exception as e:
            self.send_response(502)
            self._cors()
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps({
                "error": True,
                "reason": f"代理转发失败: {e}"
            }, ensure_ascii=False).encode())

    def send_json(self, data):
        self.send_response(200)
        self._cors()
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())

    def _cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers',
                         'Content-Type, X-TYC-Token, Authorization')

    def serve_static(self, filename):
        filepath = os.path.join(STATIC_DIR, filename)
        if not os.path.isfile(filepath):
            self.send_response(404)
            self._cors()
            self.end_headers()
            return

        ct = 'text/html; charset=utf-8'
        if filename.endswith('.js'):
            ct = 'application/javascript; charset=utf-8'
        elif filename.endswith('.css'):
            ct = 'text/css; charset=utf-8'
        elif filename.endswith('.json'):
            ct = 'application/json; charset=utf-8'
        elif filename.endswith('.png'):
            ct = 'image/png'
        elif filename.endswith('.svg'):
            ct = 'image/svg+xml'

        with open(filepath, 'rb') as f:
            data = f.read()
        self.send_response(200)
        self._cors()
        self.send_header('Content-Type', ct)
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format, *args):
        print(f"  [{self.command}] {args[0]}")


if __name__ == '__main__':
    server = http.server.HTTPServer(('0.0.0.0', PROXY_PORT), ProxyHandler)
    print(f"""
╔══════════════════════════════════════════════╗
║  天眼查地址反查 · 代理服务器                   ║
╠══════════════════════════════════════════════╣
║  代理地址: http://127.0.0.1:{PROXY_PORT}            ║
║  前端页面: http://127.0.0.1:{PROXY_PORT}            ║
║  API 转发: {TYC_API_BASE}  ║
║  按 Ctrl+C 停止                               ║
╚══════════════════════════════════════════════╝
""")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n代理已停止。")
        server.shutdown()
