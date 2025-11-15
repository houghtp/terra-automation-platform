#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Adds CIS benchmark metadata to check files from CSV source
.DESCRIPTION
    Reads metadata from CIS CSV file and embeds it as JSON in each check file
    for reporting and dashboard purposes
#>

param(
    [string]$CsvPath = "C:\Users\hough\Repos\CSPM Scripts\M365\CIS_Microsoft_365_Foundations_Benchmark_v5.0.0.csv",
    [string]$ChecksPath = ".\checks"
)

# Load CSV data
Write-Host "Loading CIS metadata from CSV..." -ForegroundColor Cyan
$cisData = Import-Csv $CsvPath

# Get all check files
$checkFiles = Get-ChildItem -Path $ChecksPath -Recurse -Filter "*.ps1"

Write-Host "Found $($checkFiles.Count) check files" -ForegroundColor Green
Write-Host "Processing checks..." -ForegroundColor Cyan

$processed = 0
$skipped = 0

foreach ($checkFile in $checkFiles) {
    # Extract check ID from filename (e.g., "1.2.2" from "1.2.2_ensure_sign-in_to_shared_mailboxes_is_blocked.ps1")
    if ($checkFile.Name -match '^(\d+\.\d+\.\d+)_') {
        $checkId = $matches[1]

        # Find matching metadata in CSV
        $metadata = $cisData | Where-Object { $_.'Recommendation ID' -eq $checkId }

        if ($metadata) {
            # Read current file content
            $content = Get-Content $checkFile.FullName -Raw

            # Check if metadata already exists
            if ($content -match '# CIS_METADATA_START') {
                Write-Host "  ⊘ $checkId - Metadata already exists, skipping" -ForegroundColor Yellow
                $skipped++
                continue
            }

            # Build metadata block as JSON embedded in PowerShell comment
            $metadataJson = @{
                RecommendationId = $metadata.'Recommendation ID'
                Level = $metadata.Level
                Title = $metadata.Title
                Section = $metadata.Section
                SubSection = $metadata.'Sub-Section'
                ProfileApplicability = $metadata.'Profile Applicability'
                Description = $metadata.Description
                Rationale = $metadata.Rationale
                Impact = $metadata.Impact
                Audit = $metadata.Audit
                Remediation = $metadata.Remediation
                DefaultValue = $metadata.'Default Value'
                References = $metadata.References
                CISControls = $metadata.'CIS Controls'
            } | ConvertTo-Json -Compress -Depth 10

            # Create metadata block
            $metadataBlock = @"
<# CIS_METADATA_START
$metadataJson
CIS_METADATA_END #>

"@

            # Find the first line (should be "# Control: X.X.X")
            $lines = $content -split "`r?`n"
            $firstNonEmptyLine = 0
            for ($i = 0; $i -lt $lines.Count; $i++) {
                if ($lines[$i] -match '\S') {
                    $firstNonEmptyLine = $i
                    break
                }
            }

            # Insert metadata after the first comment line
            $newContent = ($lines[0..$firstNonEmptyLine] -join "`n") + "`n" + $metadataBlock + ($lines[($firstNonEmptyLine + 1)..($lines.Count - 1)] -join "`n")

            # Write updated content
            Set-Content -Path $checkFile.FullName -Value $newContent -NoNewline

            Write-Host "  ✓ $checkId - Metadata added" -ForegroundColor Green
            $processed++
        }
        else {
            Write-Host "  ⊘ $checkId - No matching metadata found in CSV" -ForegroundColor Yellow
            $skipped++
        }
    }
    else {
        Write-Host "  ⊘ $($checkFile.Name) - Could not extract check ID from filename" -ForegroundColor Yellow
        $skipped++
    }
}

Write-Host "`nSummary:" -ForegroundColor Cyan
Write-Host "  Processed: $processed" -ForegroundColor Green
Write-Host "  Skipped: $skipped" -ForegroundColor Yellow
Write-Host "  Total: $($checkFiles.Count)" -ForegroundColor White
