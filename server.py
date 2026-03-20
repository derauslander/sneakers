#!/usr/bin/env python3
"""
The Vault — Local Web Server
Serves sneaker-vault.html and handles image uploads to the Shoes folder.
Run from C:/DerAuslander with: python server.py
Then open: http://localhost:8000/sneaker-vault.html
"""

import http.server
import json
import os
import shutil
from urllib.parse import urlparse, parse_qs

PORT = 8000
SHOES_DIR = "Shoes"

class VaultHandler(http.server.SimpleHTTPRequestHandler):

    def do_POST(self):
        """Handle image upload: POST /upload?key=4_Fire+Red&type=main"""
        if self.path.startswith("/upload"):
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            key  = params.get("key",  [""])[0]   # e.g. "4_Fire Red"
            kind = params.get("type", ["main"])[0] # "main" or "hover"

            if not key:
                self._respond(400, {"error": "Missing key parameter"})
                return

            # Build filename: "4_Fire Red.png" or "4_Fire Red_hover.png"
            suffix = "_hover" if kind == "hover" else ""
            filename = f"{key}{suffix}.png"
            filepath = os.path.join(SHOES_DIR, filename)

            # Read uploaded file data
            length = int(self.headers.get("Content-Length", 0))
            data = self.rfile.read(length)

            # Ensure Shoes directory exists
            os.makedirs(SHOES_DIR, exist_ok=True)

            # Save the file
            with open(filepath, "wb") as f:
                f.write(data)

            self._respond(200, {"path": f"Shoes/{filename}", "key": key})

        elif self.path.startswith("/delete"):
            """Handle image delete: POST /delete?key=4_Fire+Red&type=main"""
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            key  = params.get("key",  [""])[0]
            kind = params.get("type", ["main"])[0]

            suffix = "_hover" if kind == "hover" else ""
            filename = f"{key}{suffix}.png"
            filepath = os.path.join(SHOES_DIR, filename)

            if os.path.exists(filepath):
                os.remove(filepath)
                self._respond(200, {"deleted": filename})
            else:
                self._respond(404, {"error": "File not found"})
        else:
            self._respond(404, {"error": "Not found"})

    def _respond(self, status, data):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        """Handle CORS preflight"""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def log_message(self, format, *args):
        """Custom log format"""
        print(f"  {args[0]} {args[1]}")

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    print(f"\n  ╔══════════════════════════════════════╗")
    print(f"  ║        THE VAULT — LOCAL SERVER      ║")
    print(f"  ╠══════════════════════════════════════╣")
    print(f"  ║  http://localhost:{PORT}/sneaker-vault.html  ║")
    print(f"  ║  Press Ctrl+C to stop               ║")
    print(f"  ╚══════════════════════════════════════╝\n")
    httpd = http.server.HTTPServer(("", PORT), VaultHandler)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n  Server stopped.")
