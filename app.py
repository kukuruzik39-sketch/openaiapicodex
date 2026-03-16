import requests
from flask import Flask, request, Response
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

HOST_ROUTING = {
    "auth0.openai.com": "https://auth0.openai.com",
    "auth.openai.com":  "https://auth.openai.com",
    "api.openai.com":   "https://api.openai.com",
}

@app.route("/", defaults={"path": ""}, methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
@app.route("/<path:path>", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
def proxy(path):
    original_host = request.headers.get("X-Original-Host", "").split(":")[0].lower()
    incoming_host = request.headers.get("Host", "").split(":")[0].lower()
    check_host = original_host or incoming_host
    target_url = None
    host = None
    for target_host, base_url in HOST_ROUTING.items():
        if check_host == target_host:
            target_url = f"{base_url}/{path}"
            host = target_host
            logging.info(f"HOST MATCH: {check_host} -> {target_url}")
            break
    if target_url is None:
        if path.startswith("v1/"):
            target_url = f"https://api.openai.com/{path}"
            host = "api.openai.com"
        else:
            return Response("Not found", 404)
    headers = {}
    for k, v in request.headers.items():
        if k.lower() not in ["host", "content-length", "x-forwarded-for", "x-real-ip", "via", "x-request-id", "cf-ray", "cf-connecting-ip", "x-original-host"]:
            headers[k] = v
    headers["Host"] = host
    try:
        resp = requests.request(method=request.method, url=target_url, headers=headers, data=request.get_data(), allow_redirects=True, stream=True, timeout=120)
        def generate():
            for chunk in resp.iter_content(chunk_size=4096):
                yield chunk
        excluded = ["content-encoding", "content-length", "transfer-encoding", "connection"]
        resp_headers = [(n, v) for (n, v) in resp.raw.headers.items() if n.lower() not in excluded]
        return Response(generate(), resp.status_code, resp_headers)
    except Exception as e:
        logging.error(f"Proxy error: {e}")
        return Response(str(e), 500)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
