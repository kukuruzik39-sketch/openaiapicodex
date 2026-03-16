from flask import Flask, request, Response
import urllib.request
import urllib.error
import logging
import os
import ssl
import json

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

ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

@app.route('/', defaults={'path': ''}, methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'])
@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'])
def proxy(path):
    try:
        original_host = request.headers.get('X-Original-Host', 'api.openai.com')
        target_base = HOST_ROUTING.get(original_host, 'https://api.openai.com')
        
        if path:
            target_url = f"{target_base}/{path}"
        else:
            target_url = target_base
        
        if request.query_string:
            target_url += '?' + request.query_string.decode('utf-8')
        
        # Log request details
        logger.info(f"=== REQUEST ===")
        logger.info(f"Method: {request.method}")
        logger.info(f"Path: {path}")
        logger.info(f"Target: {target_url}")
        logger.info(f"Headers: {dict(request.headers)}")
        
        body = request.get_data()
        if body:
            try:
                logger.info(f"Body: {json.loads(body)}")
            except:
                logger.info(f"Body (raw): {body[:200]}")
        
        headers = {}
        for key, value in request.headers:
            if key.lower() not in ['host', 'x-original-host']:
                headers[key] = value
        
        req = urllib.request.Request(
            target_url,
            data=body or None,
            headers=headers,
            method=request.method
        )
        
        with urllib.request.urlopen(req, context=ssl_context, timeout=30) as response:
            content = response.read()
            status = response.status
            
            logger.info(f"Response status: {status}")
            
            response_headers = []
            for key, value in response.headers.items():
                if key.lower() not in ['content-encoding', 'content-length', 'transfer-encoding', 'connection']:
                    response_headers.append((key, value))
            
            return Response(content, status, response_headers)
    
    except urllib.error.HTTPError as e:
        logger.error(f"HTTP Error: {e.code} {e.reason}")
        logger.error(f"Response: {e.read()}")
        return Response(e.read(), e.code)
    
    except Exception as e:
        logger.error(f"Proxy error: {e}", exc_info=True)
        return {"error": str(e)}, 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port)
