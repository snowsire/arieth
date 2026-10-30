"""Serve Feishin and proxy its music API, bound only to this PC's loopback."""
import http.client
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
WEB = ROOT / 'web'
HOP_HEADERS = {'connection','keep-alive','proxy-authenticate','proxy-authorization','te','trailer','transfer-encoding','upgrade'}


class PhonePlayer(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB), **kwargs)

    def log_message(self, message, *args):
        # API query strings can include login tokens: never log them.
        print(self.log_date_time_string(), self.command, urlsplit(self.path).path, flush=True)

    def end_headers(self):
        self.send_header('X-Content-Type-Options', 'nosniff')
        if not self.is_api() and not urlsplit(self.path).path.startswith('/assets/'):
            self.send_header('Cache-Control', 'no-store')
        super().end_headers()

    def list_directory(self, path):
        self.send_error(404)
        return None

    def is_api(self):
        path = urlsplit(self.path).path
        return path == '/navidrome' or path.startswith('/navidrome/')

    def proxy_api(self):
        # Reject ambiguous framing before reading or forwarding the body.
        lengths = self.headers.get_all('Content-Length', [])
        if self.headers.get('Transfer-Encoding') or len(lengths) > 1:
            self.send_error(400, 'Unsupported request framing')
            self.close_connection = True
            return
        try:
            length = lengths[0] if lengths else '0'
            if not length.isascii() or not length.isdecimal():
                raise ValueError
            size = int(length)
        except ValueError:
            self.send_error(400, 'Invalid Content-Length')
            self.close_connection = True
            return
        if size > 16 * 1024 * 1024:
            self.send_error(413)
            self.close_connection = True
            return
        backend = http.client.HTTPConnection('127.0.0.1', 4533, timeout=60)
        started = False
        try:
            body = self.rfile.read(size) if size else None
            connection_headers = {key.strip().lower() for key in self.headers.get('Connection', '').split(',')}
            headers = {k:v for k,v in self.headers.items() if k.lower() not in HOP_HEADERS | connection_headers | {'host','accept-encoding'}}
            headers['Host'] = '127.0.0.1:4533'
            headers['Accept-Encoding'] = 'identity'
            target = urlsplit(self.path)
            path = target.path[len('/navidrome'):] or '/'
            if target.query:
                path += '?' + target.query
            backend.request(self.command, path, body=body, headers=headers)
            response = backend.getresponse()
            self.send_response(response.status, response.reason)
            connection_headers = {key.strip().lower() for key in response.getheader('Connection', '').split(',')}
            for key, value in response.getheaders():
                if key.lower() not in HOP_HEADERS | connection_headers | {'server','date'}:
                    self.send_header(key, value)
            self.end_headers()
            started = True
            if self.command != 'HEAD':
                while True:
                    data = response.read(65536)
                    if not data:
                        break
                    self.wfile.write(data)
        except (OSError, http.client.HTTPException):
            # Avoid emitting upstream URLs or credential-bearing headers.
            self.close_connection = True
            if not started:
                try:
                    self.send_error(502, 'Music server unavailable')
                except OSError:
                    pass  # The client may have disconnected as well.
        finally:
            backend.close()

    def do_GET(self):
        if self.is_api():
            self.proxy_api()
        else:
            super().do_GET()

    def do_HEAD(self):
        if self.is_api():
            self.proxy_api()
        else:
            super().do_HEAD()

    def do_POST(self):
        if self.is_api():
            self.proxy_api()
        else:
            self.send_error(405)

    do_PUT = do_POST
    do_DELETE = do_POST
    do_PATCH = do_POST


if __name__ == '__main__':
    if not (WEB / 'index.html').is_file():
        raise SystemExit('Feishin web assets are not installed')
    log = open(ROOT / 'phone-server.log', 'a', encoding='utf-8', buffering=1)
    sys.stdout = log
    sys.stderr = log
    server = ThreadingHTTPServer(('127.0.0.1', 9180), PhonePlayer)
    print('Snow Music phone player listening on loopback port 9180', flush=True)
    server.serve_forever()
