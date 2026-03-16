from flask import Flask, request, Response
import urllib.request
import urllib.error
import logging
import os
import ssl

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Host routing map
HOST_ROUTING = {
    'auth.openai.com': 'https://auth.openai.com',
    'auth0.openai.com': 'https://auth0.openai.com',
    'api.openai.com': 'https://api.openai.com',
}

# Create SSL context that doesn't verify certificates (for corporate proxies)
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

@app.route('/', defaults={'path': ''}, methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'])
@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'])
def proxy(path):
    try:
        # Get original host from header
        original_host = request.headers.get('X-Original-Host', 'api.openai.com')
        
        # Smart routing based on path for web-production-9a07
        if original_host == 'web-production-9a07.up.railway.app':
            if path.startswith('oauth/') or path.startswith('authorize'):
                target_base = 'https://auth.openai.com'
            else:
                target_base = 'https://api.openai.com'
        else:
            # Get target URL from routing map
            target_base = HOST_ROUTING.get(original_host, 'https://api.openai.com')
        
        # Build full URL
        if path:
            target_url = f"{target_base}/{path}"
        else:
            target_url = target_base
        
        # Add query string
        if request.query_string:
            target_url += '?' + request.query_string.decode('utf-8')
        
        logger.info(f"Proxying {request.method} {path} -> {target_url}")
        
        # Build headers
        headers = {}
        for key, value in request.headers:
            if key.lower() not in ['host', 'x-original-host']:
                headers[key] = value
        
        # Create request
        req = urllib.request.Request(
            target_url,
            data=request.get_data() or None,
            headers=headers,
            method=request.method
        )
        
        # Forward request
        with urllib.request.urlopen(req, context=ssl_context, timeout=30) as response:
            # Read response
            content = response.read()
            status = response.status
            
            # Log response for debugging
            logger.info(f"Response status: {status}")
            logger.info(f"Response headers: {dict(response.headers)}")
            logger.info(f"Response body (first 500 chars): {content[:500]}")
            
            # Build response headers
            response_headers = []
            for key, value in response.headers.items():
                if key.lower() not in ['content-encoding', 'content-length', 'transfer-encoding', 'connection']:
                    response_headers.append((key, value))
            
            return Response(content, status, response_headers)
    
    except urllib.error.HTTPError as e:
        logger.error(f"HTTP Error: {e.code} {e.reason}")
        return Response(e.read(), e.code)
    
    except Exception as e:
        logger.error(f"Proxy error: {e}", exc_info=True)
        return {"error": str(e)}, 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port)
