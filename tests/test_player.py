"""Offline regression checks. No real music server or credentials are used."""
import contextlib
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
import io
import json
from pathlib import Path
import socket
import tempfile
import threading
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


proxy = load('phone_server', 'phone-server.py')
setup = load('setup_web', 'setup-web.py')
extract = load('extract_web', 'extract-web.py')


class Backend(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/unavailable':
            self.connection.close()
            return
        body = self.rfile.read(int(self.headers.get('Content-Length', '0')))
        payload = json.dumps({'path': self.path, 'body': body.decode(),
                              'private': self.headers.get('X-Private'),
                              'range': self.headers.get('Range')}).encode()
        self.send_response(206 if self.headers.get('Range') else 200)
        self.send_header('Content-Length', str(len(payload)))
        self.send_header('Connection', 'X-Upstream')
        self.send_header('X-Upstream', 'must not forward')
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        if self.command != 'HEAD':
            self.wfile.write(payload)

    do_POST = do_GET
    do_HEAD = do_GET
    do_PUT = do_GET
    do_PATCH = do_GET
    do_DELETE = do_GET

    def log_message(self, *args):
        pass


class ProxyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.web = Path(cls.temp.name)
        (cls.web / 'index.html').write_text('Arieth', encoding='utf-8')
        (cls.web / 'mobile-polish.js').write_text('// custom', encoding='utf-8')
        (cls.web / 'private').mkdir()
        cls.backend = ThreadingHTTPServer(('127.0.0.1', 0), Backend)
        cls.frontend = ThreadingHTTPServer(('127.0.0.1', 0), proxy.PhonePlayer)
        original = http.client.HTTPConnection
        cls.web_patch = patch.object(proxy, 'WEB', cls.web)
        cls.connection_patch = patch.object(proxy.http.client, 'HTTPConnection',
            side_effect=lambda *a, **kw: original('127.0.0.1', cls.backend.server_port, **kw))
        cls.web_patch.start()
        cls.connection_patch.start()
        cls.connection = original
        cls.threads = [threading.Thread(target=s.serve_forever, daemon=True)
                       for s in (cls.backend, cls.frontend)]
        for thread in cls.threads:
            thread.start()

    @classmethod
    def tearDownClass(cls):
        for server in (cls.frontend, cls.backend):
            server.shutdown()
            server.server_close()
        for thread in cls.threads:
            thread.join()
        cls.connection_patch.stop()
        cls.web_patch.stop()
        cls.temp.cleanup()

    def request(self, method, path, body=None, headers=None):
        connection = self.connection('127.0.0.1', self.frontend.server_port, timeout=3)
        try:
            connection.request(method, path, body, headers or {})
            response = connection.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            connection.close()

    def test_api_query_at_mount_and_subpath(self):
        for path, expected in [('/navidrome?f=json', '/?f=json'),
                               ('/navidrome/rest/ping.view?t=secret', '/rest/ping.view?t=secret')]:
            with self.subTest(path=path):
                status, _, body = self.request('GET', path)
                self.assertEqual(status, 200)
                self.assertEqual(json.loads(body)['path'], expected)
        self.assertEqual(self.request('GET', '/navidromeevil')[0], 404)

    def test_methods_bodies_and_head(self):
        for method in ('POST', 'PUT', 'PATCH', 'DELETE'):
            with self.subTest(method=method):
                status, _, body = self.request(method, '/navidrome/auth/login', 'sample')
                self.assertEqual(status, 200)
                self.assertEqual(json.loads(body)['body'], 'sample')
        status, headers, body = self.request('HEAD', '/navidrome/rest/ping.view')
        self.assertEqual(status, 200)
        self.assertGreater(int(headers['Content-Length']), 0)
        self.assertEqual(body, b'')
        self.assertEqual(self.request('POST', '/index.html', '')[0], 405)

    def test_hop_headers_and_ranges(self):
        status, headers, body = self.request('GET', '/navidrome/rest/stream.view', headers={
            'Connection': 'X-Private', 'X-Private': 'secret', 'Range': 'bytes=0-10'})
        self.assertEqual(status, 206)
        self.assertNotIn('X-Upstream', headers)
        data = json.loads(body)
        self.assertIsNone(data['private'])
        self.assertEqual(data['range'], 'bytes=0-10')

    def test_invalid_request_framing(self):
        for length, expected in [('oops', 400), ('-1', 400), ('+1', 400), ('16777217', 413)]:
            with self.subTest(length=length):
                self.assertEqual(self.request('POST', '/navidrome/auth/login',
                    headers={'Content-Length': length})[0], expected)
        self.assertEqual(self.request('POST', '/navidrome/auth/login',
            headers={'Transfer-Encoding': 'chunked'})[0], 400)
        with socket.create_connection(('127.0.0.1', self.frontend.server_port), timeout=3) as conn:
            conn.sendall(b'POST /navidrome HTTP/1.0\r\nContent-Length: 0\r\nContent-Length: 1\r\n\r\n')
            self.assertIn(b'400', conn.recv(1024).split(b'\r\n')[0])

    def test_upstream_failure(self):
        status, _, body = self.request('GET', '/navidrome/unavailable')
        self.assertEqual(status, 502)
        self.assertNotIn(b'127.0.0.1:4533', body)

    def test_static_and_log_privacy(self):
        for path in ('/', '/mobile-polish.js?v=5'):
            status, headers, _ = self.request('GET', path)
            self.assertEqual(status, 200)
            self.assertEqual(headers['Cache-Control'], 'no-store')
            self.assertEqual(headers['X-Content-Type-Options'], 'nosniff')
        self.assertEqual(self.request('GET', '/private/')[0], 404)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.request('GET', '/navidrome/rest/ping.view?t=secret-password')
        self.assertNotIn('secret-password', output.getvalue())


class SetupTests(unittest.TestCase):
    def test_reinstall_is_idempotent_and_manifest_covers_app(self):
        with tempfile.TemporaryDirectory() as folder:
            web = Path(folder)
            (web / 'assets').mkdir()
            (web / 'assets' / 'manifest.webmanifest').write_text(json.dumps({
                'icons': [{'src': '32x32.png'}], 'screenshots': []}), encoding='utf-8')
            (web / 'index.html').write_text('<html><head><title>Feishin</title>'
                '<link rel="manifest" href="./assets/manifest.webmanifest">'
                '</head><body></body></html>', encoding='utf-8')
            setup.customize(web)
            before = (web / 'index.html').read_text(encoding='utf-8')
            setup.customize(web)
            self.assertEqual((web / 'index.html').read_text(encoding='utf-8'), before)
            self.assertEqual(before.count('mobile-polish.js'), 1)
            self.assertIn('Arieth - Snow Music', before)
            manifest = json.loads((web / 'manifest.webmanifest').read_text(encoding='utf-8'))
            self.assertEqual(manifest['scope'], '/')
            self.assertEqual(manifest['icons'][0]['src'], './assets/32x32.png')

    def test_checksum_mismatch(self):
        with patch.object(extract, 'request', return_value=io.BytesIO(b'wrong')):
            with self.assertRaisesRegex(ValueError, 'digest mismatch'):
                extract.verified_bytes('https://example.invalid/blob', 'sha256:bad', 'unused')


if __name__ == '__main__':
    unittest.main()
