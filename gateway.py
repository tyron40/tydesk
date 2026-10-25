"""ZDesk's new address forwards to the existing authoritative broker."""
import os
import threading
from urllib.parse import quote
import requests
from flask import Flask, Response, request, stream_with_context, render_template, jsonify

# Fixed destination: clients can never select an arbitrary proxy target.
UPSTREAM = 'https://tydesk-broker.onrender.com'
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 21 * 1024 * 1024
local = threading.local()

# Public pages and downloads are local so a sleeping broker cannot replace the
# dashboard with Render's 502 page. The existing broker has a durable registry.
from browser_routes import install as install_browser
install_browser(app, durable_devices=True)


@app.get('/')
def index():
    return render_template('index.html', durable_devices=True)


@app.after_request
def headers(response):
    response.headers['Cache-Control'] = 'no-store'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' blob:; media-src 'self' blob:; frame-ancestors 'none'"
    return response


def starting():
    response = jsonify(error='backend_starting', message='ZDesk is starting. Please wait a moment.')
    response.status_code = 503
    response.headers['Retry-After'] = '3'
    return response


@app.get('/healthz')
def health():
    return {'service': 'ZDesk gateway', 'ready': True}


@app.route('/<path:path>', methods=['GET', 'HEAD', 'POST', 'PUT', 'DELETE', 'OPTIONS'])
def forward(path):
    if not hasattr(local, 'session'):
        local.session = requests.Session()
        local.session.trust_env = False
    headers = {k: v for k, v in request.headers if k.lower() in (
        'authorization', 'content-type', 'accept', 'range', 'if-range', 'if-none-match', 'x-filename')
        or k.lower().startswith(('x-allow-', 'x-audio-', 'x-companion-', 'x-tydesk-', 'x-remote-'))}
    headers['Accept-Encoding'] = 'identity'
    url = UPSTREAM + '/' + quote(path, safe='/')
    if request.query_string:
        url += '?' + request.query_string.decode('ascii', errors='replace')
    try:
        # Prepare independently so no previous client's cookies or authorization
        # can be inherited from the thread's pooled transport session.
        prepared = requests.Request(request.method, url, headers=headers, data=request.get_data()).prepare()
        remote = local.session.send(prepared, timeout=(10, 90), stream=True, allow_redirects=False)
    except requests.RequestException:
        return starting()
    if remote.status_code in (502, 503, 504):
        remote.close()
        return starting()
    excluded = {'connection', 'keep-alive', 'proxy-authenticate', 'proxy-authorization',
        'te', 'trailer', 'transfer-encoding', 'upgrade', 'content-encoding', 'content-length', 'set-cookie'}
    connection_headers = {s.strip().lower() for s in remote.headers.get('Connection', '').split(',')}
    response_headers = {k: v for k, v in remote.headers.items() if k.lower() not in excluded | connection_headers}
    if response_headers.get('Location', '').startswith(UPSTREAM + '/'):
        response_headers['Location'] = response_headers['Location'][len(UPSTREAM):]
    response_headers['Cache-Control'] = 'no-store'

    def chunks():
        try:
            yield from remote.iter_content(64 * 1024)
        finally:
            remote.close()
    response = Response(stream_with_context(chunks()), status=remote.status_code, headers=response_headers)
    response.call_on_close(remote.close)
    return response


if __name__ == '__main__':
    from waitress import serve
    serve(app, host='0.0.0.0', port=int(os.environ.get('PORT', '10000')), threads=32)
