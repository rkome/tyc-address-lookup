"""阿里云函数计算 FC 入口"""
import json, os, ssl, urllib.request, urllib.error, traceback

TYC_API_BASE = "https://open.api.tianyancha.com"

# 静态文件内联（避免路径问题）
_APP_HTML = None

def handler(event, context):
    try:
        return _handle(event)
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'text/plain; charset=utf-8', 'Access-Control-Allow-Origin': '*'},
            'body': f"Error: {e}\n\n{traceback.format_exc()}"
        }

def _handle(event):
    # FC 3.0 HTTP 触发器 event 格式
    method = (event.get('requestContext', {}).get('http', {}).get('method', '') or
              event.get('httpMethod', '') or 'GET').upper()
    path = (event.get('rawPath', '') or event.get('path', '/')).split('?')[0]
    query = event.get('rawQueryString', '') or ''
    headers = event.get('headers', {})

    if method == 'OPTIONS':
        return _cors_response()

    if path == '/ping':
        return _json({'ok': True, 'service': 'TYC Proxy @ FC'})

    if path.startswith('/tyc/'):
        return _proxy(path, query, headers)

    return _serve_html()

def _proxy(path, query, headers):
    api_path = path.replace('/tyc', '', 1)
    query_part = f'?{query}' if query else ''
    target_url = TYC_API_BASE + api_path + query_part
    token = headers.get('x-tyc-token', headers.get('X-TYC-Token', ''))

    req = urllib.request.Request(target_url)
    req.add_header('Authorization', token)

    try:
        with urllib.request.urlopen(req, context=ssl.create_default_context(), timeout=25) as resp:
            data = resp.read().decode('utf-8')
            try:
                json.loads(data)
            except:
                return _json({'error': True, 'reason': 'API返回非JSON', 'raw': data[:300]}, 502)
            return {'statusCode': resp.status, 'headers': {'Content-Type': 'application/json; charset=utf-8', 'Access-Control-Allow-Origin': '*'}, 'body': data}
    except urllib.error.HTTPError as e:
        data = e.read().decode('utf-8', errors='replace')
        return {'statusCode': e.code, 'headers': {'Content-Type': 'application/json; charset=utf-8', 'Access-Control-Allow-Origin': '*'}, 'body': data}
    except Exception as e:
        return _json({'error': True, 'reason': str(e)}, 502)

def _serve_html():
    global _APP_HTML
    if _APP_HTML is None:
        try:
            with open(os.path.join(os.path.dirname(__file__), 'app_2.html'), 'r', encoding='utf-8') as f:
                _APP_HTML = f.read()
        except:
            # 回退：尝试当前目录
            try:
                with open('app_2.html', 'r', encoding='utf-8') as f:
                    _APP_HTML = f.read()
            except:
                return _text('app_2.html not found', 404)
    return {'statusCode': 200, 'headers': {'Content-Type': 'text/html; charset=utf-8', 'Access-Control-Allow-Origin': '*'}, 'body': _APP_HTML}

def _json(data, status=200):
    return {'statusCode': status, 'headers': {'Content-Type': 'application/json; charset=utf-8', 'Access-Control-Allow-Origin': '*'}, 'body': json.dumps(data, ensure_ascii=False)}

def _text(text, status=200):
    return {'statusCode': status, 'headers': {'Content-Type': 'text/plain; charset=utf-8', 'Access-Control-Allow-Origin': '*'}, 'body': text}

def _cors_response():
    return {'statusCode': 200, 'headers': {'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Methods': 'GET,POST,OPTIONS', 'Access-Control-Allow-Headers': 'Content-Type,X-TYC-Token,Authorization'}, 'body': ''}
