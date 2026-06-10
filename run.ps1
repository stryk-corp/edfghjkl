# Windows PowerShell startup script for UniClear
Set-StrictMode -Version Latest

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

Write-Host "=== UniClear - University Clearance System ==="
Write-Host ""

if (-not (Test-Path ".\venv")) {
    Write-Host "Creating virtual environment..."
    if (Get-Command py -ErrorAction SilentlyContinue) {
        py -m venv .\venv
    } else {
        python -m venv .\venv
    }
}

$activateScript = Join-Path $ProjectRoot "venv\Scripts\Activate.ps1"
if (-not (Test-Path $activateScript)) {
    Write-Error "Virtual environment activation script not found: $activateScript"
    exit 1
}

Write-Host "Activating virtual environment..."
. $activateScript

Write-Host "Installing dependencies..."
python -m pip install -q --upgrade pip
python -m pip install -q -r requirements.txt

Write-Host "Creating required directories..."
New-Item -ItemType Directory -Force -Path uploads, certificates | Out-Null

if (-not (Test-Path ".\.env")) {
    Copy-Item .env.example .env
    Write-Host "Created .env from template"
}

Write-Host ""
Write-Host "Starting server..."
Write-Host "  -> Student Portal : http://127.0.0.1:6001/frontend/student.html"
Write-Host "  -> Officer Portal  : http://127.0.0.1:6001/frontend/officer.html"
Write-Host "  -> Admin Dashboard : http://127.0.0.1:6001/frontend/admin.html"
Write-Host "  -> Verify Cert     : http://127.0.0.1:6001/frontend/verify.html"
Write-Host "  -> API Docs        : http://127.0.0.1:6001/docs"
Write-Host ""
Write-Host "Demo accounts:"
Write-Host "  Student : student@university.edu / student123"
Write-Host "  Officer : library@university.edu / officer123"
Write-Host "  Admin   : admin@university.edu   / admin123"
Write-Host ""

if (Get-Command py -ErrorAction SilentlyContinue) {
    py -m uvicorn backend.main:app --host 127.0.0.1 --port 6001
} else {
    python -m uvicorn backend.main:app --host 127.0.0.1 --port 6001
}
