"""Loopback-only checks for legacy launchers' aggregate compatibility."""
import importlib.util
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import tempfile
import threading
import unittest
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('local_server', ROOT / 'scripts/local-dashboard-server.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
PATHS = ['/data/' + name + '.json' for name in ('health', 'insights', 'weekly', 'ra', 'config/tracked-projects')]

class Source(BaseHTTPRequestHandler):
    hits = []
    redirect = False
    def do_GET(self):
        type(self).hits.append((self.command, self.path))
        if type(self).redirect:
            self.send_response(302)
            self.send_header('Location', '/not-approved')
            self.end_headers()
            return
        body = ('{"fixture":"' + self.path + '"}').encode()
        self.send_response(200)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    do_HEAD = do_GET
    def log_message(self, *args): pass

class QuietHandler(module.DashboardHandler):
    def log_message(self, *args): pass

class LocalContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.source = ThreadingHTTPServer(('127.0.0.1', 0), Source)
        QuietHandler.upstream = 'http://127.0.0.1:' + str(cls.source.server_port)
        cls.local = ThreadingHTTPServer(('127.0.0.1', 0), partial(QuietHandler, directory=cls.tmp.name))
        cls.url = 'http://127.0.0.1:' + str(cls.local.server_port)
        for server in (cls.source, cls.local):
            threading.Thread(target=server.serve_forever, daemon=True).start()
    @classmethod
    def tearDownClass(cls):
        for server in (cls.local, cls.source):
            server.shutdown(); server.server_close()
        cls.tmp.cleanup()
    def setUp(self): Source.hits = []; Source.redirect = False
    def request(self, path, method='GET'):
        try: return urllib.request.urlopen(urllib.request.Request(self.url + path, method=method), timeout=3)
        except urllib.error.HTTPError as error: return error
    def test_five_fixed_aggregate_paths_get_and_head(self):
        for path in PATHS:
            with self.request(path) as response:
                self.assertEqual(response.status, 200)
                payload = response.read()
                self.assertEqual(payload, ('{"fixture":"' + path + '"}').encode())
                self.assertEqual(response.headers['Cache-Control'], 'no-store')
            with self.request(path, 'HEAD') as response:
                self.assertEqual(response.status, 200)
                self.assertEqual(response.read(), b'')
                self.assertEqual(int(response.headers['Content-Length']), len(payload))
        self.assertEqual(Source.hits, [('GET', path) for path in PATHS for _ in range(2)])
    def test_query_is_not_forwarded(self):
        with self.request(PATHS[0] + '?destination=http://example.invalid') as response:
            self.assertEqual(response.status, 200)
        self.assertEqual(Source.hits, [('GET', PATHS[0])])
    def test_unknown_runtime_and_writes_never_reach_source(self):
        for path in ('/runtime/dashboard', '/data/not-approved.json', '/data/../health.json', '/http://example.invalid'):
            with self.request(path) as response: self.assertEqual(response.code, 404)
        for method in ('POST', 'PUT', 'PATCH', 'DELETE'):
            with self.request(PATHS[0], method) as response: self.assertGreaterEqual(response.code, 400)
        self.assertEqual(Source.hits, [])
    def test_aggregate_redirect_is_not_followed(self):
        Source.redirect = True
        with self.request(PATHS[0]) as response: self.assertEqual(response.code, 502)
        self.assertEqual(Source.hits, [('GET', PATHS[0])])
    def test_existing_op_proxy_is_preserved(self):
        with self.request('/op/users/me?synthetic=1') as response:
            self.assertEqual(response.status, 200)
        self.assertEqual(Source.hits, [('GET', '/op/users/me?synthetic=1')])

if __name__ == '__main__': unittest.main()
