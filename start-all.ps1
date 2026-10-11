$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$ragDir = Join-Path $root "rag-service"
$backendDir = Join-Path $root "backend-node"
$frontendDir = Join-Path $root "frontend"
$ragVenvPython = Join-Path $ragDir ".venv\Scripts\python.exe"

Write-Host "Starting YouTube Summary Studio services..." -ForegroundColor Cyan

$portInUse = Get-NetTCPConnection -LocalPort 4000 -ErrorAction SilentlyContinue | Select-Object -First 1
if ($portInUse) {
    Stop-Process -Id $portInUse.OwningProcess -Force
    Write-Host "Stopped stale process on port 4000: $($portInUse.OwningProcess)"
}

if (-not (Test-Path $ragVenvPython)) {
    & py -3.12 -m venv (Join-Path $ragDir ".venv")
}

& $ragVenvPython -m pip install -r (Join-Path $ragDir "requirements.txt")

Start-Process -FilePath "powershell" -ArgumentList "-NoProfile", "-ExecutionPolicy", "Bypass", "-NoExit", "-Command", "Set-Location '$ragDir'; & '.venv\Scripts\python.exe' -m uvicorn main:app --host 0.0.0.0 --port 8001" -WorkingDirectory $ragDir
Start-Process -FilePath "powershell" -ArgumentList "-NoProfile", "-ExecutionPolicy", "Bypass", "-NoExit", "-Command", "Set-Location '$backendDir'; npm start" -WorkingDirectory $backendDir
Start-Process -FilePath "powershell" -ArgumentList "-NoProfile", "-ExecutionPolicy", "Bypass", "-NoExit", "-Command", "Set-Location '$frontendDir'; npm run dev -- --host 0.0.0.0" -WorkingDirectory $frontendDir

Write-Host "RAG service started in a new terminal window."
Write-Host "Node backend started in a new terminal window."
Write-Host "Frontend started in a new terminal window."
Write-Host "Open http://localhost:5173 to use the app."
Write-Host "If a service fails, check its terminal window for errors."
