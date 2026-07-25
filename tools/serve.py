#!/usr/bin/env python3
"""Serve dist/ the way Vercel will, for local checking.

    python tools/serve.py [port]

Applies the vercel.json rules that affect whether a URL resolves - cleanUrls,
trailingSlash and the redirect table - so a page that works here works on
Vercel. `vercel dev` is the real thing but needs an authenticated account; this
needs nothing. It does not run api/contact.js (Node), so form POSTs answer 501.
"""

import http.server
import json
import mimetypes
import os
import posixpath
import socketserver
import sys
import urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(ROOT, "dist")

mimetypes.add_type("image/avif", ".avif")
mimetypes.add_type("image/webp", ".webp")
mimetypes.add_type("font/otf", ".otf")
mimetypes.add_type("application/json", ".json")

with open(os.path.join(ROOT, "vercel.json"), encoding="utf-8") as fh:
    CFG = json.load(fh)

REDIRECTS = {r["source"].rstrip("/") or "/": r["destination"]
             for r in CFG.get("redirects", [])}


class Handler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        pass

    # api/contact.js is a Node function this server cannot execute, but it
    # answers the two statuses the real one does for non-POST/POST, so
    # tools/smoke.py gives the same verdict here as against Vercel.
    def do_POST(self):
        if self.path == "/api/contact":
            self.send_error(501, "api/contact.js needs `vercel dev` or Node")
        else:
            self.send_error(405)

    def _api_stub(self):
        if self.path != "/api/contact":
            return False
        if not os.path.isfile(os.path.join(ROOT, "api", "contact.js")):
            return False
        self.send_response(405)          # matches the real handler's GET reply
        self.send_header("Allow", "POST")
        self.send_header("Content-Type", "application/json; charset=utf-8")
        body = b'{"ok":false,"error":"Method not allowed"}'
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
        return True

    def do_HEAD(self):
        self.do_GET(head_only=True)

    def do_GET(self, head_only=False):
        if self._api_stub():
            return
        path = urllib.parse.urlparse(self.path).path
        path = urllib.parse.unquote(path)

        target = REDIRECTS.get(path.rstrip("/") or "/")
        if target:
            self.send_response(308)
            self.send_header("Location", target)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return

        # trailingSlash: false
        if len(path) > 1 and path.endswith("/"):
            self.send_response(308)
            self.send_header("Location", path.rstrip("/"))
            self.send_header("Content-Length", "0")
            self.end_headers()
            return

        rel = posixpath.normpath(path).lstrip("/")
        candidates = []
        if path == "/":
            candidates = ["index.html"]
        else:
            candidates = [rel]
            if not os.path.splitext(rel)[1]:      # cleanUrls
                candidates += [rel + ".html", posixpath.join(rel, "index.html")]

        for cand in candidates:
            full = os.path.join(DIST, cand.replace("/", os.sep))
            if os.path.isfile(full):
                return self._send(full, head_only)

        notfound = os.path.join(DIST, "404.html")
        if os.path.isfile(notfound):
            return self._send(notfound, head_only, status=404)
        self.send_error(404)

    def _send(self, full, head_only, status=200):
        ctype = mimetypes.guess_type(full)[0] or "application/octet-stream"
        if ctype.startswith("text/") or ctype in (
                "application/javascript", "application/json", "image/svg+xml"):
            ctype += "; charset=utf-8"
        size = os.path.getsize(full)
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(size))
        self.end_headers()
        if head_only:
            return
        with open(full, "rb") as fh:
            while True:
                chunk = fh.read(65536)
                if not chunk:
                    break
                self.wfile.write(chunk)


class Server(socketserver.ThreadingTCPServer):
    daemon_threads = True
    allow_reuse_address = True


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 3111
    with Server(("127.0.0.1", port), Handler) as httpd:
        print("serving dist/ on http://127.0.0.1:%d (Ctrl-C to stop)" % port)
        httpd.serve_forever()
