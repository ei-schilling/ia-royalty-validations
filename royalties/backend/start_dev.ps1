# Kill processes on port 8000 and start dev backend
$ErrorActionPreference = "SilentlyContinue"

# Kill anything on port 8000
Get-NetTCPConnection -LocalPort 8000 | ForEach-Object { 
    Stop-Process -Id $_.OwningProcess -Force 
}

Start-Sleep -Seconds 2

# Start the backend
Set-Location "C:\Users\ei\Projects\royaltyStatementValidator\royalties\backend"
& ".venv\Scripts\python.exe" run_dev.py
