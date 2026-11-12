# Starts the Django API (port 8000) and the Vite dev server (port 5173).
# Usage: powershell -ExecutionPolicy Bypass -File scripts\dev.ps1
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    Write-Error "Environnement Python introuvable. Voir README.md, section Installation."
    exit 1
}

$backend = Start-Process -PassThru -NoNewWindow -FilePath $python `
    -ArgumentList "manage.py", "runserver", "8000" -WorkingDirectory (Join-Path $root "backend")

try {
    Push-Location (Join-Path $root "frontend")
    npm run dev
} finally {
    Pop-Location
    if ($backend -and -not $backend.HasExited) { Stop-Process -Id $backend.Id -Force }
}