<#>
.SYNOPSIS
    Preflight check for IoT Anomaly Detection System
    Verifies system readiness before demo or deployment

.DESCRIPTION
    Performs GO/NO-GO checks:
    1. ADMIN_PASSWORD environment variable is set
    2. Port 8000 is free
    3. Model artifacts match freeze.json hashes
    4. Frontend build exists
    5. Default tests pass
    6. Serial port is visible (warning only)

.OUTPUTS
    Returns exit code 0 for GO, non-zero for NO-GO
    Prints detailed results to console
#>

param(
    [switch]$SkipTests,
    [switch]$Verbose
)

$ErrorActionPreference = "Stop"
$PROJECT_ROOT = Split-Path -Parent $PSScriptRoot
$RESULTS_DIR = Join-Path $PROJECT_ROOT "results"

function Write-Status {
    param($Message, $Status)
    $color = switch ($Status) {
        "PASS" { "Green" }
        "FAIL" { "Red" }
        "WARN" { "Yellow" }
        default { "White" }
    }
    Write-Host "[$Status] $Message" -ForegroundColor $color
}

function Test-AdminPassword {
    if ($env:ADMIN_PASSWORD) {
        Write-Status "ADMIN_PASSWORD is set" "PASS"
        return $true
    } else {
        Write-Status "ADMIN_PASSWORD is NOT set" "FAIL"
        return $false
    }
}

function Test-Port8000 {
    $listener = $null
    try {
        $listener = [System.Net.Sockets.TcpListener]::New([System.Net.IPAddress]::IPv6Any, 8000)
        $listener.Start()
        $listener.Stop()
        Write-Status "Port 8000 is free" "PASS"
        return $true
    } catch {
        Write-Status "Port 8000 is in use" "FAIL"
        return $false
    } finally {
        if ($listener) { $listener.Stop() }
    }
}

function Test-ModelHashes {
    $freezePath = Join-Path $RESULTS_DIR "freeze.json"
    if (-not (Test-Path $freezePath)) {
        Write-Status "results/freeze.json not found" "FAIL"
        return $false
    }
    
    $freeze = Get-Content $freezePath | ConvertFrom-Json
    $allPass = $true
    
    foreach ($file in $freeze.files.Keys) {
        $fullPath = Join-Path $PROJECT_ROOT $file
        if (-not (Test-Path $fullPath)) {
            Write-Status "Missing file: $file" "FAIL"
            $allPass = $false
            continue
        }
        
        $actualHash = Get-FileHash -Path $fullPath -Algorithm SHA256 | Select-Object -ExpandProperty Hash
        $expectedHash = $freeze.files[$file]
        
        if ($actualHash -eq $expectedHash) {
            Write-Status "Hash match: $file" "PASS"
        } else {
            Write-Status "Hash MISMATCH: $file`n  Expected: $expectedHash`n  Actual:   $actualHash" "FAIL"
            $allPass = $false
        }
    }
    
    # Check commit hash
    $currentCommit = git rev-parse HEAD 2>$null
    if ($currentCommit -and $freeze.commit_hash) {
        if ($currentCommit.StartsWith($freeze.commit_hash.Substring(0, 8))) {
            Write-Status "Commit hash matches: $($currentCommit.Substring(0,8))" "PASS"
        } else {
            Write-Status "Commit hash MISMATCH`n  Expected: $($freeze.commit_hash.Substring(0,8))`n  Actual:   $($currentCommit.Substring(0,8))" "FAIL"
            $allPass = $false
        }
    }
    
    return $allPass
}

function Test-FrontendBuild {
    $distPath = Join-Path $PROJECT_ROOT "frontend" "dist"
    $indexPath = Join-Path $distPath "index.html"
    $assetsPath = Join-Path $distPath "assets"
    
    if (-not (Test-Path $indexPath)) {
        Write-Status "Frontend build not found (missing index.html)" "FAIL"
        return $false
    }
    
    if (-not (Test-Path $assetsPath)) {
        Write-Status "Frontend assets directory not found" "WARN"
        # Not a hard failure
    }
    
    Write-Status "Frontend build exists" "PASS"
    return $true
}

function Test-DefaultTests {
    if ($SkipTests) {
        Write-Status "Skipping default test run (--SkipTests)" "WARN"
        return $true
    }
    
    try {
        $result = python -m pytest tests/ -q --tb=no 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Status "Default tests pass" "PASS"
            return $true
        } else {
            Write-Status "Default tests FAILED" "FAIL"
            if ($Verbose) { Write-Host $result }
            return $false
        }
    } catch {
        Write-Status "Test execution failed" "FAIL"
        return $false
    }
}

function Test-SerialPort {
    try {
        $ports = python -c "
import serial.tools.list_ports
ports = []
for p in __import__('serial.tools.list_ports').comports():
    desc = p.description or ''
    if 'bluetooth' not in desc.lower():
        ports.append(p.device)
print(' '.join(ports))
"
        if ($ports) {
            Write-Status "Serial ports detected: $ports" "PASS"
        } else {
            Write-Status "No serial ports detected (warning only)" "WARN"
        }
        return $true
    } catch {
        Write-Status "Serial port detection failed" "WARN"
        return $true
    }
}

# Main preflight execution
Write-Host "=== IoT Anomaly Detection Preflight Check ===" -ForegroundColor Cyan
Write-Host "Project: $PROJECT_ROOT"
Write-Host ""

$results = @{}

$results.AdminPassword = Test-AdminPassword
$results.Port8000 = Test-Port8000
$results.ModelHashes = Test-ModelHashes
$results.FrontendBuild = Test-FrontendBuild
$results.DefaultTests = Test-DefaultTests
$results.SerialPort = Test-SerialPort

Write-Host ""
Write-Host "=== PREFLIGHT SUMMARY ===" -ForegroundColor Cyan

$allPass = $true
foreach ($key in $results.Keys) {
    $status = if ($results[$key]) { "GO" } else { "NO-GO" }
    $color = if ($results[$key]) { "Green" } else { "Red" }
    Write-Host "$key : $status" -ForegroundColor $color
    if (-not $results[$key]) { $allPass = $false }
}

Write-Host ""
if ($allPass) {
    Write-Host "=== GO: System ready for demo/deployment ===" -ForegroundColor Green
    exit 0
} else {
    Write-Host "=== NO-GO: System NOT ready ===" -ForegroundColor Red
    exit 1
}