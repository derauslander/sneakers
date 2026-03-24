@echo off
if not exist backups mkdir backups
if exist index.html (
  echo Backing up index.html...
  powershell -Command "Copy-Item 'index.html' ('backups\index_' + (Get-Date -Format 'yyyy-MM-dd_HHmm') + '.html')"
  echo Backup saved to backups folder.
)
echo Building index.html from sneaker-vault.html...
powershell -Command "(Get-Content 'sneaker-vault.html') -replace 'const ADMIN_MODE = true;', 'const ADMIN_MODE = false;' | Set-Content 'index.html'"
echo Done!
