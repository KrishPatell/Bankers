from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PAGE = ROOT / "clipboard-capture.html"
OUTPUT = ROOT / "article8-source.txt"


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/clipboard-capture.html":
            self.send_error(404)
            return
        body = PAGE.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path != "/capture":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", "0"))
        OUTPUT.write_bytes(self.rfile.read(length))
        self.send_response(204)
        self.end_headers()

    def log_message(self, *_args):
        pass


HTTPServer(("127.0.0.1", 3113), Handler).serve_forever()
