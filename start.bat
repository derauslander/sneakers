@echo off
cd /d C:\DerAuslander\sneakers
echo Starting The Vault...
start "" python server.py
timeout /t 2 /nobreak >nul
start "" chrome "http://localhost:8000/sneaker-vault.html"
