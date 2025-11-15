# PowerShell Linting and Validation Script
# This script validates PowerShell syntax and applies best practices analysis

param(
    [string]$Path = "checks",
    [switch]$Fix,
    [string[]]$Severity = @("Error", "Warning"),
    [switch]$Detailed
)

# Import required modules
try {
    Import-Module PSScriptAnalyzer -ErrorAction Stop
    Write-Host "✅ PSScriptAnalyzer loaded successfully" -ForegroundColor Green
} catch {
    Write-Host "❌ PSScriptAnalyzer not found. Installing..." -ForegroundColor Red
    Install-Module -Name PSScriptAnalyzer -Force -Scope CurrentUser
    Import-Module PSScriptAnalyzer
    Write-Host "✅ PSScriptAnalyzer installed and loaded" -ForegroundColor Green
}

function Test-PowerShellSyntax {
    param([string]$FilePath)

    $errors = $null
    $content = Get-Content $FilePath -Raw -ErrorAction SilentlyContinue

    if (-not $content) {
        return @{
            HasSyntaxErrors = $true
            Errors = @("Could not read file content")
        }
    }

    # Parse the script to check for syntax errors
    [void][System.Management.Automation.PSParser]::Tokenize($content, [ref]$errors)

    return @{
        HasSyntaxErrors = $errors.Count -gt 0
        Errors = $errors | ForEach-Object { "Line $($_.Token.StartLine): $($_.Message)" }
    }
}

function Invoke-PowerShellLinting {
    param([string]$TargetPath)

    Write-Host "🔍 Starting PowerShell linting process..." -ForegroundColor Cyan
    Write-Host "Target: $TargetPath" -ForegroundColor Gray
    Write-Host "Severity levels: $($Severity -join ', ')" -ForegroundColor Gray
    Write-Host ""

    # Get all PowerShell files
    $psFiles = Get-ChildItem -Path $TargetPath -Filter "*.ps1" -Recurse
    Write-Host "Found $($psFiles.Count) PowerShell files to analyze" -ForegroundColor Yellow
    Write-Host ""

    $totalIssues = 0
    $totalSyntaxErrors = 0
    $filesWithIssues = 0
    $results = @{}

    foreach ($file in $psFiles) {
        Write-Host "📄 Analyzing: $($file.Name)" -ForegroundColor White

        # 1. Syntax validation
        $syntaxResult = Test-PowerShellSyntax -FilePath $file.FullName

        if ($syntaxResult.HasSyntaxErrors) {
            $totalSyntaxErrors++
            Write-Host "  ❌ SYNTAX ERRORS:" -ForegroundColor Red
            $syntaxResult.Errors | ForEach-Object {
                Write-Host "    $_" -ForegroundColor Red
            }
        } else {
            Write-Host "  ✅ Syntax: OK" -ForegroundColor Green
        }

        # 2. PSScriptAnalyzer rules
        $analysisResults = Invoke-ScriptAnalyzer -Path $file.FullName -Severity $Severity

        if ($analysisResults) {
            $filesWithIssues++
            $fileIssueCount = $analysisResults.Count
            $totalIssues += $fileIssueCount

            Write-Host "  ⚠️ Found $fileIssueCount issues:" -ForegroundColor Yellow

            $analysisResults | Group-Object Severity | ForEach-Object {
                $severityColor = switch ($_.Name) {
                    "Error" { "Red" }
                    "Warning" { "Yellow" }
                    "Information" { "Cyan" }
                    default { "Gray" }
                }

                Write-Host "    $($_.Name): $($_.Count)" -ForegroundColor $severityColor

                if ($Detailed) {
                    $_.Group | ForEach-Object {
                        Write-Host "      Line $($_.Line): [$($_.RuleName)] $($_.Message)" -ForegroundColor $severityColor
                    }
                }
            }
        } else {
            Write-Host "  ✅ Analysis: Clean" -ForegroundColor Green
        }

        $results[$file.Name] = @{
            SyntaxErrors = $syntaxResult.HasSyntaxErrors
            SyntaxErrorDetails = $syntaxResult.Errors
            AnalysisIssues = $analysisResults
            IssueCount = if ($analysisResults) { $analysisResults.Count } else { 0 }
        }

        Write-Host ""
    }

    # Summary
    Write-Host "=" * 60 -ForegroundColor Cyan
    Write-Host "📊 LINTING SUMMARY" -ForegroundColor Cyan
    Write-Host "=" * 60 -ForegroundColor Cyan
    Write-Host "Files analyzed: $($psFiles.Count)" -ForegroundColor White
    Write-Host "Files with syntax errors: $totalSyntaxErrors" -ForegroundColor $(if ($totalSyntaxErrors -gt 0) { "Red" } else { "Green" })
    Write-Host "Files with analysis issues: $filesWithIssues" -ForegroundColor $(if ($filesWithIssues -gt 0) { "Yellow" } else { "Green" })
    Write-Host "Total issues found: $totalIssues" -ForegroundColor $(if ($totalIssues -gt 0) { "Yellow" } else { "Green" })

    # Exit code for CI/CD
    $exitCode = if ($totalSyntaxErrors -gt 0) { 2 } elseif ($totalIssues -gt 0) { 1 } else { 0 }
    Write-Host "Exit code: $exitCode" -ForegroundColor $(if ($exitCode -eq 0) { "Green" } elseif ($exitCode -eq 1) { "Yellow" } else { "Red" })

    return @{
        ExitCode = $exitCode
        Results = $results
        Summary = @{
            TotalFiles = $psFiles.Count
            SyntaxErrors = $totalSyntaxErrors
            FilesWithIssues = $filesWithIssues
            TotalIssues = $totalIssues
        }
    }
}

# Run the linting process
$result = Invoke-PowerShellLinting -TargetPath $Path

# Optional: Auto-fix some issues
if ($Fix) {
    Write-Host ""
    Write-Host "🔧 AUTO-FIX MODE ENABLED" -ForegroundColor Magenta
    Write-Host "Attempting to fix automatically resolvable issues..." -ForegroundColor Magenta

    # You could add auto-fix logic here for common issues
    # For now, we'll just show what could be auto-fixed
    Write-Host "Auto-fix capabilities could include:" -ForegroundColor Gray
    Write-Host "  - Trailing whitespace removal" -ForegroundColor Gray
    Write-Host "  - Null comparison ordering" -ForegroundColor Gray
    Write-Host "  - Consistent indentation" -ForegroundColor Gray
    Write-Host "  - Variable naming conventions" -ForegroundColor Gray
}

exit $result.ExitCode