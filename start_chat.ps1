$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot

$env:PYTHONUNBUFFERED = 1

$pythonPath = "D:\anaconda3\envs\智能体框架\python.exe"

if (-not (Test-Path $pythonPath)) {
    Write-Host "Python not found at: $pythonPath" -ForegroundColor Red
    Write-Host "Please check your conda environment." -ForegroundColor Red
    Write-Host "Press any key to exit..."
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    exit 1
}

Write-Host "Starting... Close this window or press Ctrl+C to stop."
& $pythonPath dev_up.py --backend-reload

Write-Host "Press any key to exit..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
