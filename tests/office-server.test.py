"""Synthetic, loopback-only contract checks; no OP data or credentials."""
import importlib.util
import json
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('office_server', ROOT / 'deploy/windows/dashboard_server.py')
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

class Source(BaseHTTPRequestHandler):
    hits = []
    redirect = False
    def do_GET(self):
        type(self).hits.append(self.path)
        if type(self).redirect:
            self.send_response(302)
            self.send_header('Location', '/not-an-approved-source')
            self.end_headers()
            return
        body = json.dumps({'fixture_path': self.path}).encode()
        self.send_response(200)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def log_message(self, *args):
        pass

class QuietHandler(MODULE.Handler):
    def log_message(self, *args):
        pass

class MirrorContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.web = Path(cls.tmp.name)
        for name in set(MODULE.ASSETS.values()):
            (cls.web / name).write_text('synthetic ' + name, encoding='utf-8')
        cls.source = ThreadingHTTPServer(('127.0.0.1', 0), Source)
        cls.origin = 'http://127.0.0.1:' + str(cls.source.server_port)
        cls.mirror = ThreadingHTTPServer(('127.0.0.1', 0), partial(QuietHandler, web_root=cls.web, source=cls.origin))
        cls.url = 'http://127.0.0.1:' + str(cls.mirror.server_port)
        for server in (cls.source, cls.mirror):
            threading.Thread(target=server.serve_forever, daemon=True).start()
    @classmethod
    def tearDownClass(cls):
        for server in (cls.mirror, cls.source):
            server.shutdown()
            server.server_close()
        cls.tmp.cleanup()
    def setUp(self):
        Source.hits = []
        Source.redirect = False
    def request(self, path, method='GET'):
        try:
            return urllib.request.urlopen(urllib.request.Request(self.url + path, method=method), timeout=3)
        except urllib.error.HTTPError as error:
            return error
    def test_five_fixed_paths_preserve_payload(self):
        for path in sorted(MODULE.DATA_PATHS):
            with self.request(path) as response:
                self.assertEqual(response.status, 200)
                self.assertEqual(json.load(response), {'fixture_path': path})
                self.assertEqual(response.headers['Cache-Control'], 'no-store')
        self.assertEqual(Source.hits, sorted(MODULE.DATA_PATHS))
    def test_unknown_and_write_requests_do_not_reach_source(self):
        for path in ('/runtime/dashboard', '/data/not-approved.json', '/../secret', '/server.py'):
            with self.request(path) as response:
                self.assertEqual(response.code, 404)
        for method in ('POST', 'PUT', 'PATCH', 'DELETE'):
            with self.request('/data/health.json', method) as response:
                self.assertEqual(response.code, 405)
        self.assertEqual(Source.hits, [])
    def test_redirect_is_failure_not_followed(self):
        Source.redirect = True
        with self.request('/data/health.json') as response:
            self.assertEqual(response.code, 502)
        self.assertEqual(Source.hits, ['/data/health.json'])
    def test_query_cannot_change_upstream_path(self):
        with self.request('/data/health.json?destination=not-approved') as response:
            self.assertEqual(response.status, 200)
        self.assertEqual(Source.hits, ['/data/health.json'])
    def test_assets_and_head(self):
        for path in ('/', '/executive-app.js?v=cache-test', '/style.css'):
            with self.request(path) as response:
                self.assertEqual(response.status, 200)
        with self.request('/data/health.json', 'HEAD') as response:
            self.assertEqual(response.status, 200)
            self.assertEqual(response.read(), b'')
    def test_cli_rejects_unrestricted_bind_and_invalid_origin(self):
        script = str(ROOT / 'deploy/windows/dashboard_server.py')
        for source, bind in ((self.origin, '0.0.0.0'), ('http://example.invalid/path', '127.0.0.1'), ('ftp://example.invalid', '127.0.0.1')):
            result = subprocess.run([sys.executable, script, '--web-root', str(self.web), '--source', source, '--bind', bind], capture_output=True, timeout=4)
            self.assertEqual(result.returncode, 2)

if __name__ == '__main__':
    unittest.main()