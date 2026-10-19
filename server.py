"""ALPG server: JSON API under /api plus the static frontend, standard library only.

    python server.py                  # http://127.0.0.1:8000
    python server.py --port 9000 --db ./data/alpg.db

Environment: ALPG_DB, ALPG_SECRET, ALPG_SEED_DEMO (default 1), ALPG_CORS_ORIGIN (default *),
ALPG_FRONTEND_DIR, ALPG_TOKEN_TTL, ALPG_PBKDF2_ITERATIONS.
"""
import argparse
import json
import mimetypes
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qsl, unquote, urlsplit

import db
import routes
import security

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DB = os.path.join(HERE, "data", "alpg.db")
DEFAULT_FRONTEND = os.path.normpath(os.path.join(HERE, "..", "frontend"))

mimetypes.add_type("text/javascript", ".js")
mimetypes.add_type("text/css", ".css")


class Handler(BaseHTTPRequestHandler):
    server_version = "ALPG/0.3"
    sys_version = ""  # do not advertise the Python version

    # --- helpers ---
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", os.environ.get("ALPG_CORS_ORIGIN", "*"))
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, OPTIONS")
        self.send_header("Access-Control-Max-Age", "600")

    def _send(self, status, body: bytes, ctype, extra=None, api=False):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        if api:
            self.send_header("Cache-Control", "no-store")
            self._cors()
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _json(self, status, payload, extra=None):
        self._send(status, json.dumps(payload).encode("utf-8"), "application/json; charset=utf-8", extra, api=True)

    def log_message(self, fmt, *args):  # one short line per request on stderr
        sys.stderr.write("%s %s\n" % (self.address_string(), fmt % args))

    # --- routing ---
    def _handle(self):
        parts = urlsplit(self.path)
        path = parts.path
        if path.startswith("/api/") or path == "/api":
            query = dict(parse_qsl(parts.query, keep_blank_values=True))
            raw = b""
            if self.command in ("POST", "PUT"):
                try:
                    length = int(self.headers.get("Content-Length") or 0)
                except ValueError:
                    return self._json(400, {"error": {"code": "bad_request", "message": "Invalid Content-Length."}})
                if length > routes.MAX_BODY_BYTES:  # refuse without reading the upload, then drop the connection
                    self.close_connection = True
                    return self._json(413, {"error": {"code": "too_large", "message": "Request body is too large."}},
                                      {"Connection": "close"})
                raw = self.rfile.read(length) if length > 0 else b""
            status, payload, extra = routes.dispatch(
                self.command, path.rstrip("/") or "/", query, raw, self.headers, self.client_address[0],
                self.server.db_path, self.server.secret)
            return self._json(status, payload, extra)
        if self.command not in ("GET", "HEAD"):
            return self._send(405, b"Method not allowed", "text/plain; charset=utf-8", {"Allow": "GET, HEAD"})
        self._static(path)

    def _static(self, path):
        root = os.path.realpath(self.server.frontend_dir)
        rel = unquote(path).lstrip("/") or "index.html"
        full = os.path.realpath(os.path.join(root, rel))
        if os.path.isdir(full):
            full = os.path.join(full, "index.html")
        # block path traversal (../) and symlinks that leave the frontend folder
        if not (full == root or full.startswith(root + os.sep)) or not os.path.isfile(full):
            return self._send(404, b"Not found", "text/plain; charset=utf-8")
        ctype = mimetypes.guess_type(full)[0] or "application/octet-stream"
        if ctype.startswith("text/") or ctype in ("application/json",):
            ctype += "; charset=utf-8"
        with open(full, "rb") as f:
            self._send(200, f.read(), ctype, {"Cache-Control": "no-cache"})

    def do_GET(self): self._handle()
    def do_HEAD(self): self._handle()
    def do_POST(self): self._handle()
    def do_PUT(self): self._handle()

    def do_DELETE(self):
        self._send(405, b"Method not allowed", "text/plain; charset=utf-8")

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.send_header("Content-Length", "0")
        self.end_headers()


class AlpgServer(ThreadingHTTPServer):
    daemon_threads = True


def make_server(host="127.0.0.1", port=8000, db_path=DEFAULT_DB, frontend_dir=DEFAULT_FRONTEND, seed=True):
    db.init_db(db_path)
    if seed:
        db.seed_demo(db_path)
    srv = AlpgServer((host, port), Handler)
    srv.db_path = db_path
    srv.frontend_dir = frontend_dir
    srv.secret = security.get_secret(os.path.join(os.path.dirname(os.path.abspath(db_path)), ""))
    return srv


def main():
    ap = argparse.ArgumentParser(description="ALPG API + frontend server")
    ap.add_argument("--host", default="127.0.0.1", help="bind address (default 127.0.0.1, this computer only)")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--db", default=os.environ.get("ALPG_DB", DEFAULT_DB))
    ap.add_argument("--frontend", default=os.environ.get("ALPG_FRONTEND_DIR", DEFAULT_FRONTEND))
    args = ap.parse_args()
    seed = os.environ.get("ALPG_SEED_DEMO", "1") != "0"
    srv = make_server(args.host, args.port, args.db, args.frontend, seed)
    print(f"ALPG running at http://{args.host}:{args.port}  (database: {args.db})")
    if seed:
        print("Demo accounts: student@alpg.demo / mentor@alpg.demo / faculty@alpg.demo  password: demo123")
        print("Set ALPG_SEED_DEMO=0 to disable demo accounts for a real deployment.")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
