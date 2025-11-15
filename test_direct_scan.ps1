# Direct test of Start-Checks.ps1 with hardcoded credentials
$ErrorActionPreference = 'Stop'

# Hardcoded auth params
$AuthParams = @{
    TenantId = "660636d5-cb4e-4816-b1b8-f5afc446f583"
    TenantDomain = "terrait.co.uk"  # REQUIRED for certificate-based auth!
    SharePointAdminUrl = "https://netorgft16254533-admin.sharepoint.com/"
    ClientId = "REDACTED_AZURE_CLIENT_ID"
    ClientSecret = "REDACTED_AZURE_CLIENT_SECRET"
    CertificateBase64 = "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"
    CertificatePassword = "REDACTED_CERTIFICATE_PASSWORD"
    Username = "REDACTED_USERNAME"
    Password = "QNW7swiPIUy?#v%r"
}

Write-Host "======================================" -ForegroundColor Cyan
Write-Host "Testing Start-Checks.ps1 with hardcoded credentials" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

$scriptPath = "/home/paul/repos/terra-automation-platform/app/features/msp/cspm/CIS_Microsoft_365_Foundations_Benchmark_v5.0.0/Start-Checks.ps1"

Write-Host "Calling Start-Checks.ps1 with:" -ForegroundColor Yellow
Write-Host "  - Tech: M365" -ForegroundColor Yellow
Write-Host "  - L1Only: Yes" -ForegroundColor Yellow
Write-Host "  - TenantId: $($AuthParams.TenantId)" -ForegroundColor Yellow
Write-Host "  - ClientId: $($AuthParams.ClientId)" -ForegroundColor Yellow
Write-Host "  - Has Certificate: Yes" -ForegroundColor Yellow
Write-Host ""

try {
    & $scriptPath `
        -Tech "M365" `
        -AuthParams $AuthParams `
        -L1Only `
        -ScanId "test-direct-$(Get-Date -Format 'yyyyMMddHHmmss')" `
        -OutputFormat "json"

    Write-Host ""
    Write-Host "======================================" -ForegroundColor Green
    Write-Host "✓ Script completed successfully!" -ForegroundColor Green
    Write-Host "======================================" -ForegroundColor Green
}
catch {
    Write-Host ""
    Write-Host "======================================" -ForegroundColor Red
    Write-Host "✗ Script failed with error:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host $_.ScriptStackTrace -ForegroundColor Red
    Write-Host "======================================" -ForegroundColor Red
    exit 1
}
