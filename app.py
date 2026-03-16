from flask import Flask, request, Response
import requests
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Host routing map
HOST_ROUTING = {
    'auth.openai.com': 'https://auth.openai.com',
    'auth0.openai.com': 'https://auth0.openai.com',
    'api.openai.com': 'https://api.openai.com',
    'tg-api-production.up.railway.app': 'https://api.openai.com',
}

@app.route('/', defaults={'path': ''}, methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'])
@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'])
def proxy(path):
    # Get original host from header
    original_host = request.headers.get('X-Original-Host', 'api.openai.com')
    
    # Get target URL
    target_base = HOST_ROUTING.get(original_host, 'https://api.openai.com')
    
    # Build full URL - handle both with and without leading slash
    if path:
        target_url = f"{target_base}/{path}"
    else:
        target_url = target_base
    
    logger.info(f"Proxying {request.method} {path} -> {target_url}")
    logger.info(f"Original-Host: {original_host}")
    
    # Copy headers but remove host-specific ones
    headers = {k: v for k, v in request.headers if k.lower() not in ['host', 'x-original-host']}
    
    # Forward the request
    try:
        resp = requests.request(
            method=request.method,
            url=target_url,
            headers=headers,
            data=request.get_data(),
            params=request.args,
            allow_redirects=False,
            timeout=30
        )
        
        # Build response
        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        response_headers = [(k, v) for k, v in resp.headers.items() if k.lower() not in excluded_headers]
        
        return Response(resp.content, resp.status_code, response_headers)
    
    except Exception as e:
        logger.error(f"Proxy error: {e}")
        return {"error": str(e)}, 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
