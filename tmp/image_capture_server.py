from base64 import b64decode
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent
PAGE = ROOT / "image-capture.html"


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/image-capture.html":
            self.send_error(404)
            return
        body = PAGE.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path != "/capture-image":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length))
        mime = payload.get("type", "image/png")
        extension = {"image/jpeg": ".jpg", "image/webp": ".webp", "image/gif": ".gif"}.get(mime, ".png")
        (ROOT / ("article8-clipboard-image" + extension)).write_bytes(b64decode(payload["data"]))
        self.send_response(204)
        self.end_headers()

    def log_message(self, *_args):
        pass


HTTPServer(("127.0.0.1", 3116), Handler).serve_forever()
