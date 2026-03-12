[CmdletBinding()]
param(
    [int]$BackendPort = 8000,
    [int]$FrontendPort = 5173
)

$ErrorActionPreference = "Stop"

function Ensure-Command {
    param([string]$Name)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Missing command: $Name"
    }
}

function Resolve-Python {
    $candidates = @("python", "py")
    foreach ($cmd in $candidates) {
        if (Get-Command $cmd -ErrorAction SilentlyContinue) {
            return $cmd
        }
    }
    throw "Python is not installed."
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$rootDir = Split-Path -Parent $scriptDir
$backendDir = Join-Path $rootDir "backend"
$frontendDir = Join-Path $rootDir "frontend"
$runtimeDir = Join-Path $rootDir ".runtime"

Ensure-Command -Name npm
$pythonCmd = Resolve-Python

if (-not (Test-Path $backendDir)) { throw "backend directory not found." }
if (-not (Test-Path $frontendDir)) { throw "frontend directory not found." }

Write-Host "==> [1/4] Build frontend dist..."
Push-Location $frontendDir
try {
    if (-not (Test-Path (Join-Path $frontendDir "node_modules"))) {
        npm install
    }
    npm run build
}
finally {
    Pop-Location
}

Write-Host "==> [2/4] Prepare backend virtual environment..."
Push-Location $backendDir
try {
    $venvDir = Join-Path $backendDir ".venv"
    if (-not (Test-Path $venvDir)) {
        & $pythonCmd -m venv .venv
    }

    $venvPython = Join-Path $venvDir "Scripts\\python.exe"
    if (-not (Test-Path $venvPython)) {
        # Fallback for non-Windows shells.
        $venvPython = Join-Path $venvDir "bin/python"
    }
    if (-not (Test-Path $venvPython)) {
        throw "Cannot locate Python in backend/.venv"
    }

    & $venvPython -m pip install --upgrade pip
    & $venvPython -m pip install -r requirements.txt
}
finally {
    Pop-Location
}

Write-Host "==> [3/4] Stop old processes (if any)..."
if (-not (Test-Path $runtimeDir)) {
    New-Item -ItemType Directory -Path $runtimeDir | Out-Null
}

$backendPidFile = Join-Path $runtimeDir "backend.pid"
$frontendPidFile = Join-Path $runtimeDir "frontend.pid"

foreach ($pidFile in @($backendPidFile, $frontendPidFile)) {
    if (Test-Path $pidFile) {
        $pidValue = (Get-Content $pidFile -Raw).Trim()
        if ($pidValue) {
            try {
                Stop-Process -Id ([int]$pidValue) -Force -ErrorAction Stop
            }
            catch {
                # Process may already be gone.
            }
        }
        Remove-Item $pidFile -Force
    }
}

Write-Host "==> [4/4] Start backend + frontend..."
$venvPythonForStart = Join-Path $backendDir ".venv\\Scripts\\python.exe"
if (-not (Test-Path $venvPythonForStart)) {
    $venvPythonForStart = Join-Path $backendDir ".venv/bin/python"
}

$backendProc = Start-Process -FilePath $venvPythonForStart `
    -ArgumentList @("-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "$BackendPort") `
    -WorkingDirectory $backendDir `
    -PassThru

$frontendProc = Start-Process -FilePath "npm" `
    -ArgumentList @("run", "preview", "--", "--host", "0.0.0.0", "--port", "$FrontendPort") `
    -WorkingDirectory $frontendDir `
    -PassThru

Set-Content -Path $backendPidFile -Value $backendProc.Id
Set-Content -Path $frontendPidFile -Value $frontendProc.Id

Write-Host ""
Write-Host "Deploy and start completed."
Write-Host "Frontend: http://127.0.0.1:$FrontendPort"
Write-Host "Backend : http://127.0.0.1:$BackendPort"
Write-Host "Health  : http://127.0.0.1:$BackendPort/api/health"
Write-Host ""
Write-Host "To stop services, run: .\\scripts\\stop-services.ps1"
