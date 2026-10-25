"""ZDesk's new address forwards to the existing authoritative broker."""
import os
import threading
from urllib.parse import quote
import requests
from flask import Flask, Response, request, stream_with_context

# Fixed destination: clients can never select an arbitrary proxy target.
UPSTREAM = 'https://tydesk-broker.onrender.com'
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 21 * 1024 * 1024
local = threading.local()


@app.get('/healthz')
def health():
    return {'service': 'ZDesk gateway', 'ready': True}


@app.route('/', defaults={'path': ''}, methods=['GET', 'HEAD', 'POST', 'PUT', 'DELETE', 'OPTIONS'])
@app.route('/<path:path>', methods=['GET', 'HEAD', 'POST', 'PUT', 'DELETE', 'OPTIONS'])
def forward(path):
    if not hasattr(local, 'session'):
        local.session = requests.Session()
        local.session.trust_env = False
    headers = {k: v for k, v in request.headers if k.lower() in (
        'authorization', 'content-type', 'accept', 'range', 'if-range', 'if-none-match')
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
        return Response('ZDesk is waking up or temporarily unavailable. Try again shortly.', status=503)
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
