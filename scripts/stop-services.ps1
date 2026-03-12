$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$rootDir = Split-Path -Parent $scriptDir
$runtimeDir = Join-Path $rootDir ".runtime"

if (-not (Test-Path $runtimeDir)) {
    Write-Host "No running process record found."
    exit 0
}

$stopped = $false
foreach ($name in @("backend.pid", "frontend.pid")) {
    $pidFile = Join-Path $runtimeDir $name
    if (-not (Test-Path $pidFile)) {
        continue
    }

    $pidValue = (Get-Content $pidFile -Raw).Trim()
    if ($pidValue) {
        try {
            Stop-Process -Id ([int]$pidValue) -Force -ErrorAction Stop
            Write-Host "Stopped process $pidValue"
            $stopped = $true
        }
        catch {
            Write-Host "Process $pidValue already stopped."
        }
    }

    Remove-Item $pidFile -Force
}

if (-not $stopped) {
    Write-Host "No running process was stopped."
}
