"""Private dashboard mirror: fixed aggregate reads only, no OP authentication or writes."""
import argparse
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import threading
import sys
import urllib.error
import urllib.parse
import urllib.request

DATA_PATHS = frozenset('/data/' + name + '.json' for name in
                       ('health', 'insights', 'weekly', 'ra', 'config/tracked-projects'))
ASSETS = {'/': 'PLM Dashboard.html', '/PLM%20Dashboard.html': 'PLM Dashboard.html',
          '/PLM Dashboard.html': 'PLM Dashboard.html', '/executive-app.js': 'executive-app.js',
          '/style.css': 'style.css'}
TYPES = {'.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8',
         '.css': 'text/css; charset=utf-8'}

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

SOURCE_OPENER = urllib.request.build_opener(NoRedirect())

class Handler(BaseHTTPRequestHandler):
    server_version = 'DRDashboardMirror/1'
    def __init__(self, *args, web_root, source, **kwargs):
        self.web_root, self.source = Path(web_root), source
        super().__init__(*args, **kwargs)
    def reply(self, status, body=b'', kind='text/plain; charset=utf-8', head=False):
        self.send_response(status)
        self.send_header('Content-Type', kind)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        if not head: self.wfile.write(body)
    def do_GET(self): self.read(False)
    def do_HEAD(self): self.read(True)
    def read(self, head):
        path = urllib.parse.urlsplit(self.path).path
        if path in DATA_PATHS:
            try:
                request = urllib.request.Request(self.source + path, headers={'Accept': 'application/json'}, method='GET')
                with SOURCE_OPENER.open(request, timeout=20) as response:
                    if response.status != 200: raise ValueError('Upstream response was not 200')
                    body = response.read()
                self.reply(200, body, 'application/json; charset=utf-8', head)
            except (OSError, ValueError, urllib.error.URLError):
                self.reply(502, b'Private source read failed; previous displayed data must not be treated as refreshed.', head=head)
            return
        if path == '/favicon.ico':
            self.reply(204, head=head)
            return
        asset = ASSETS.get(path)
        if asset is None:
            self.reply(404, b'Not found', head=head)
            return
        try:
            file = self.web_root / asset
            self.reply(200, file.read_bytes(), TYPES.get(file.suffix, 'application/octet-stream'), head)
        except OSError:
            self.reply(503, b'Dashboard asset unavailable', head=head)
    def do_POST(self): self.reply(405, b'Read only')
    do_PUT = do_POST
    do_PATCH = do_POST
    do_DELETE = do_POST
    def log_message(self, fmt, *args):
        # Access path/status only; no cookies, request headers, credentials, or data payloads.
        super().log_message(fmt, *args)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--web-root', required=True)
    parser.add_argument('--source', required=True)
    parser.add_argument('--bind', action='append', required=True)
    parser.add_argument('--port', type=int, default=8766)
    parser.add_argument('--log')
    args = parser.parse_args()
    if args.log:
        log_stream = open(args.log, 'a', encoding='utf-8', buffering=1)
        sys.stdout = log_stream
        sys.stderr = log_stream
    source = urllib.parse.urlsplit(args.source)
    if source.scheme not in ('http', 'https') or not source.hostname or source.username or source.password or source.query or source.fragment or source.path not in ('', '/'):
        parser.error('Source must be an HTTP(S) origin without credentials, query or path')
    web = Path(args.web_root).resolve()
    if not all((web / name).is_file() for name in set(ASSETS.values())):
        parser.error('Expected dashboard assets are missing')
    if any(bind in ('0.0.0.0', '::', '') for bind in args.bind):
        parser.error('Explicit interface addresses are required')
    handler = partial(Handler, web_root=web, source=args.source.rstrip('/'))
    servers=[]
    try:
        for bind in dict.fromkeys(args.bind):
            servers.append(ThreadingHTTPServer((bind, args.port), handler))
        for server in servers[:-1]:
            threading.Thread(target=server.serve_forever, daemon=True).start()
        print('Dashboard mirror ready on explicitly configured local interfaces', flush=True)
        servers[-1].serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        for server in servers:
            server.server_close()

if __name__ == '__main__': main()