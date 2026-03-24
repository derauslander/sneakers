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
from datetime import datetime
from urllib.parse import urlparse, parse_qs

PORT = 8000
SHOES_DIR = "Shoes"
BACKUPS_DIR = "backups"

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

        elif self.path.startswith("/backup"):
            self._handle_backup()

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

    def _handle_backup(self):
        """Handle backup: POST /backup — saves vault-data.json, archives old one"""
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length)

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            self._respond(400, {"success": False, "error": "Invalid JSON"})
            return

        os.makedirs(BACKUPS_DIR, exist_ok=True)

        # If vault-data.json exists, move it to backups with timestamp
        vault_file = "vault-data.json"
        backup_msg = ""
        if os.path.exists(vault_file):
            timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
            backup_name = f"vault-data_{timestamp}.json"
            backup_path = os.path.join(BACKUPS_DIR, backup_name)
            shutil.copy2(vault_file, backup_path)
            backup_msg = f"Old data backed up to {BACKUPS_DIR}/{backup_name}. "

        # Write new vault-data.json
        with open(vault_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        self._respond(200, {
            "success": True,
            "message": f"{backup_msg}vault-data.json updated."
        })

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
