"""阿里云函数计算 FC 入口 — 替换 proxy.py"""
import json, os, ssl, urllib.request, urllib.error

TYC_API_BASE = "https://open.api.tianyancha.com"

def handler(event, context):
    """FC HTTP 触发器入口"""
    method = event.get('httpMethod', event.get('method', 'GET')).upper()
    path = event.get('rawPath', event.get('path', '/')).split('?')[0]
    
    if method == 'OPTIONS':
        return cors({})

    if path == '/ping':
        return json_response({"ok": True, "service": "TYC Proxy @ FC"})

    if path.startswith('/tyc/'):
        return proxy_request(path, event)

    # 静态文件
    if path == '/' or path == '':
        return serve_static('app_2.html')
    return serve_static(path.lstrip('/'))

def proxy_request(path, event):
    api_path = path.replace('/tyc', '', 1)
    target_url = TYC_API_BASE + api_path + (event.get('rawQueryString') and '?' + event['rawQueryString'] or '')
    token = (event.get('headers', {}).get('x-tyc-token', '') or 
             event.get('headers', {}).get('X-TYC-Token', ''))

    req = urllib.request.Request(target_url)
    req.add_header('Authorization', token)
    req.add_header('Content-Type', 'application/json; charset=utf-8')

    try:
        with urllib.request.urlopen(req, context=ssl.create_default_context(), timeout=25) as resp:
            data = resp.read()
            try:
                json.loads(data)
            except:
                return json_response({"error": True, "reason": "天眼查API返回非JSON（可能被拦截）", "raw": data[:200].decode('utf-8', errors='replace')}, 502)
            return json_response(json.loads(data), resp.status)
    except urllib.error.HTTPError as e:
        data = e.read()
        try:
            return json_response(json.loads(data), e.code)
        except:
            return json_response({"error_code": e.code, "reason": str(e)}, e.code)
    except urllib.error.URLError as e:
        return json_response({"error": True, "reason": f"无法连接天眼查: {e.reason}"}, 502)
    except Exception as e:
        return json_response({"error": True, "reason": str(e)}, 502)

def serve_static(filename):
    filepath = os.path.join(os.path.dirname(__file__), filename)
    if not os.path.isfile(filepath):
        return text_response("Not Found", 404)
    ct = 'text/html; charset=utf-8'
    if filename.endswith('.js'): ct = 'application/javascript'
    elif filename.endswith('.css'): ct = 'text/css'
    with open(filepath, 'rb') as f:
        data = f.read()
    return {'statusCode': 200, 'headers': {'Content-Type': ct, 'Access-Control-Allow-Origin': '*'}, 'body': data.decode('utf-8'), 'isBase64Encoded': False}

def json_response(data, status=200):
    return {'statusCode': status, 'headers': {'Content-Type': 'application/json; charset=utf-8', 'Access-Control-Allow-Origin': '*'}, 'body': json.dumps(data, ensure_ascii=False), 'isBase64Encoded': False}

def text_response(text, status=200):
    return {'statusCode': status, 'headers': {'Content-Type': 'text/plain; charset=utf-8', 'Access-Control-Allow-Origin': '*'}, 'body': text, 'isBase64Encoded': False}

def cors(_):
    return {'statusCode': 200, 'headers': {'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Methods': 'GET,POST,OPTIONS', 'Access-Control-Allow-Headers': 'Content-Type,X-TYC-Token,Authorization'}, 'body': ''}
