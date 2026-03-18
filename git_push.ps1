Set-Location C:\Users\ei\Projects\royaltyStatementValidator

Write-Host "=== GIT LOG ==="
git log --oneline -5 2>&1 | ForEach-Object { Write-Host $_ }

Write-Host ""
Write-Host "=== GIT STATUS ==="
git status --short 2>&1 | ForEach-Object { Write-Host $_ }

Write-Host ""
Write-Host "=== FORCE PUSH WITH LEASE ==="
git push --force-with-lease origin main 2>&1 | ForEach-Object { Write-Host $_ }

Write-Host ""
Write-Host "=== EXIT CODE: $LASTEXITCODE ==="
