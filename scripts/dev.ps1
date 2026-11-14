# scripts/dev.ps1
# Development runner script for Windows PowerShell

param (
    [string]$AdminPassword = "admin123_change_in_production",
    [string]$SerialPort = "auto",
    [switch]$BuildFrontend = $false
)

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  Starting IoT Sensor Anomaly Detection Development Server" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# Set environment variables
$env:ADMIN_PASSWORD = $AdminPassword
$env:SERIAL_PORT = $SerialPort
$env:PYTHONUNBUFFERED = "1"

if ($BuildFrontend) {
    Write-Host "`nBuilding production frontend bundle..." -ForegroundColor Yellow
    npm --prefix frontend run build
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Frontend build failed. Aborting." -ForegroundColor Red
        exit 1
    }
}

Write-Host "`nStarting FastAPI + React application via run_ui.py..." -ForegroundColor Green
Write-Host "  • Client UI:     http://localhost:8000/" -ForegroundColor Gray
Write-Host "  • Admin Cockpit: http://localhost:8000/admin" -ForegroundColor Gray
Write-Host "  • API Docs:      http://localhost:8000/docs" -ForegroundColor Gray
Write-Host "`nPress Ctrl+C to terminate.`n" -ForegroundColor DarkGray

python run_ui.py
