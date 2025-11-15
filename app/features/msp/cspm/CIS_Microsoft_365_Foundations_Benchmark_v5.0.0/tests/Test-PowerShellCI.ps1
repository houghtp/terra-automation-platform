# CI/CD PowerShell Validation Script
# Quick validation for automated pipelines

param(
    [string]$ChecksPath = "checks",
    [switch]$FailOnWarnings = $false
)

Write-Host "🚀 Running PowerShell validation for CI/CD..." -ForegroundColor Cyan

# Quick syntax check
$syntaxErrors = 0
$warningCount = 0
$errorCount = 0

Get-ChildItem -Path $ChecksPath -Filter "*.ps1" -Recurse | ForEach-Object {
    # Syntax validation
    $errors = $null
    $content = Get-Content $_.FullName -Raw
    [void][System.Management.Automation.PSParser]::Tokenize($content, [ref]$errors)

    if ($errors) {
        $syntaxErrors++
        Write-Host "❌ SYNTAX ERROR in $($_.Name): $($errors[0].Message)" -ForegroundColor Red
    }

    # Quick PSScriptAnalyzer check (if available)
    if (Get-Module -ListAvailable -Name PSScriptAnalyzer) {
        $issues = Invoke-ScriptAnalyzer -Path $_.FullName -Severity @("Error", "Warning")
        $fileErrors = $issues | Where-Object { $_.Severity -eq "Error" }
        $fileWarnings = $issues | Where-Object { $_.Severity -eq "Warning" }

        $errorCount += $fileErrors.Count
        $warningCount += $fileWarnings.Count

        if ($fileErrors) {
            $fileErrors | ForEach-Object {
                Write-Host "❌ ERROR in $($_.ScriptName): Line $($_.Line) - $($_.Message)" -ForegroundColor Red
            }
        }

        if ($fileWarnings) {
            $fileWarnings | ForEach-Object {
                Write-Host "⚠️ WARNING in $($_.ScriptName): Line $($_.Line) - $($_.Message)" -ForegroundColor Yellow
            }
        }
    }
}

Write-Host ""
Write-Host "📊 VALIDATION RESULTS:" -ForegroundColor Cyan
Write-Host "Syntax Errors: $syntaxErrors" -ForegroundColor $(if ($syntaxErrors -gt 0) { "Red" } else { "Green" })
Write-Host "Analysis Errors: $errorCount" -ForegroundColor $(if ($errorCount -gt 0) { "Red" } else { "Green" })
Write-Host "Analysis Warnings: $warningCount" -ForegroundColor $(if ($warningCount -gt 0) { "Yellow" } else { "Green" })

# Determine exit code
if ($syntaxErrors -gt 0 -or $errorCount -gt 0) {
    Write-Host "❌ FAILED: Critical issues found" -ForegroundColor Red
    exit 1
} elseif ($FailOnWarnings -and $warningCount -gt 0) {
    Write-Host "❌ FAILED: Warnings found (fail-on-warnings enabled)" -ForegroundColor Red
    exit 1
} else {
    Write-Host "✅ PASSED: No critical issues found" -ForegroundColor Green
    exit 0
}