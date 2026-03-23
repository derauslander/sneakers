@echo off
if exist index.html (
  echo Backing up index.html to index.backup.html...
  copy /Y index.html index.backup.html >nul
)
echo Building index.html from sneaker-vault.html...
powershell -Command "(Get-Content 'sneaker-vault.html') -replace 'const ADMIN_MODE = true;', 'const ADMIN_MODE = false;' | Set-Content 'index.html'"
echo Done! index.html has been generated.
