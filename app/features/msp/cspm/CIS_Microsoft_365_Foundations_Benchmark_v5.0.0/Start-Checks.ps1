# Generic CIS Compliance Main Script
# Uses tech-specific authentication scripts based on Tech parameter
# Designed for any technology - just swap the Connect-{Tech}.ps1 script

param(
    [Parameter(Mandatory = $false)]
    [string]$Tech = "M365",

    [Parameter(Mandatory = $false)]
    [hashtable]$AuthParams = @{},

    [Parameter(Mandatory = $false)]
    [string]$OutputPath,

    [Parameter(Mandatory = $false)]
    [ValidateSet("json", "csv")]
    [string]$OutputFormat = "json",

    [Parameter(Mandatory = $false)]
    [string[]]$CheckIds,

    [Parameter(Mandatory = $false)]
    [switch]$UseExistingAuth,

    [Parameter(Mandatory = $false)]
    [switch]$WhatIf,

    [Parameter(Mandatory = $false)]
    [string]$ProgressCallbackUrl,

    [Parameter(Mandatory = $false)]
    [switch]$L1Only,

    [Parameter(Mandatory = $false)]
    [string]$ScanId
)


# Set up error handling
$ErrorActionPreference = 'Stop'

# Initialize log file path
$script:LogPath = $null

# Enhanced logging function with file output
function Write-Log {
    param([string]$Message, [string]$Level = "Info")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMessage = "[$timestamp] [$Level] $Message"

    # Determine color based on level or status keywords
    $color = "White"
    if ($Level -eq "Error" -or $Message -match "\bFail\b|\bError\b") {
        $color = "Red"
    }
    elseif ($Level -eq "Warning" -or $Message -match "\bManual\b|\bSkipped\b") {
        $color = "DarkYellow"
    }
    elseif ($Message -match "\bPass\b") {
        $color = "Green"
    }
    elseif ($Level -eq "Info") {
        $color = "Cyan"
    }

    # Console output with colors - redirect to Information stream (stream 6)
    # This ensures Write-Host output doesn't pollute stdout (stream 1)
    # Python will only capture Write-Output (stdout), not Write-Host (Information stream)
    Write-Information $logMessage -InformationAction Continue

    # File output (if log path is set)
    if ($script:LogPath -and (Test-Path (Split-Path $script:LogPath -Parent))) {
        Add-Content -Path $script:LogPath -Value $logMessage -ErrorAction SilentlyContinue
    }
}

# Progress update function
function Send-ProgressUpdate {
    param(
        [string]$Status,
        [int]$CurrentCheck,
        [int]$TotalChecks,
        [string]$CheckId = "",
        [string]$Message = ""
    )

    if (-not $ProgressCallbackUrl) { return }

    try {
        # Match Python ScanProgressUpdate schema: scan_id, progress_percentage, current_check (string), status, total_checks, passed, failed, errors
        $progressData = @{
            scan_id = $ScanId
            progress_percentage = if ($TotalChecks -gt 0) { [int][math]::Round(($CurrentCheck / $TotalChecks) * 100) } else { 0 }
            current_check = if ($CheckId) { $CheckId } else { $null }
            status = $Status
            total_checks = $TotalChecks
            passed = $null
            failed = $null
            errors = $null
        }

        $jsonPayload = $progressData | ConvertTo-Json -Compress
        Invoke-RestMethod -Uri $ProgressCallbackUrl -Method POST -Body $jsonPayload -ContentType "application/json" -TimeoutSec 3 -ErrorAction SilentlyContinue
    }
    catch {
        # Silently continue if progress updates fail
    }
}

# Generic authentication function - calls tech-specific authentication script
function Connect-Services {
    param(
        [string]$Tech,
        [hashtable]$AuthParams
    )

    Write-Log "Starting authentication for technology: $Tech"
    Write-Log "Auth parameters provided: $($AuthParams.Keys -join ', ')"

    # Build auth script name from tech parameter
    $authScript = "Connect-$Tech.ps1"
    $authScriptPath = Join-Path $PSScriptRoot $authScript

    if (-not (Test-Path $authScriptPath)) {
        throw "Authentication script not found: $authScript"
    }

    Write-Log "Using authentication script: $authScript"

    try {
        # Dot-source the auth script to get the function
        . $authScriptPath

        # Call the connection function with splatting
        $functionName = "Connect-$Tech"
        if (Get-Command $functionName -ErrorAction SilentlyContinue) {
            $authResult = & $functionName @AuthParams

            if ($authResult.Status -eq "Success") {
                Write-Log "$Tech services authentication completed successfully"
                return @{
                    TechType = $authResult.TechType
                    AuthManager = $null
                }
            } else {
                throw "Authentication failed: $($authResult.Error)"
            }
        } else {
            throw "Function $functionName not found in $authScript"
        }
    }
    catch {
        Write-Log "Failed to authenticate services: $($_.Exception.Message)" -Level "Error"
        throw
    }
}
function Get-ComplianceChecks {
    param(
        [string]$TechType,
        [string[]]$CheckIds,
        [bool]$L1Only = $false
    )

    # Look for checks in tech-specific subdirectory first, then fallback to generic checks folder
    $possibleChecksPaths = @(
        (Join-Path $PSScriptRoot "checks\$TechType"),
        (Join-Path $PSScriptRoot "checks")
    )

    $checksPath = $null
    foreach ($path in $possibleChecksPaths) {
        if (Test-Path $path) {
            $checksPath = $path
            break
        }
    }

    if (-not $checksPath) {
        throw "Checks directory not found for $TechType. Tried paths: $($possibleChecksPaths -join ', ')"
    }

    # If L1Only is specified, modify the checks path to only include L1 folder
    if ($L1Only) {
        $l1Path = Join-Path $checksPath "L1"
        if (Test-Path $l1Path) {
            $checksPath = $l1Path
            Write-Log "Loading $TechType L1 checks only from: $checksPath"
        } else {
            Write-Log "Warning: L1Only specified but L1 folder not found at: $l1Path. Loading all checks." -Level "Warning"
            Write-Log "Loading $TechType checks from: $checksPath"
        }
    } else {
        Write-Log "Loading $TechType checks from: $checksPath"
    }

    $allChecks = @()
    $checkFiles = Get-ChildItem -Path $checksPath -Filter "*.ps1" -Recurse

    foreach ($file in $checkFiles) {
        $checkInfo = @{
            Path = $file.FullName
            CheckId = $file.BaseName
            Category = $file.Directory.Name
            TechType = $TechType
            Metadata = (Get-CheckMetadata -CheckPath $file.FullName)
        }

        # Filter by CheckIds if specified
        if ($CheckIds -and $checkInfo.CheckId -notin $CheckIds) {
            continue
        }

        $allChecks += $checkInfo
    }

    Write-Log "Found $($allChecks.Count) $TechType compliance checks to execute"
    return $allChecks
}

# Extract CIS metadata from check file
function Get-CheckMetadata {
    param([string]$CheckPath)

    try {
        $content = Get-Content $CheckPath -Raw

        # Look for metadata block between CIS_METADATA_START and CIS_METADATA_END
        if ($content -match '# CIS_METADATA_START\s*(.*?)\s*CIS_METADATA_END #>') {
            $jsonString = $matches[1]
            $metadata = $jsonString | ConvertFrom-Json
            return $metadata
        }
    }
    catch {
        Write-Verbose "Could not extract metadata from $CheckPath`: $($_.Exception.Message)"
    }

    return $null
}

# Categorize checks by service dependency
function Get-CheckServiceCategory {
    param([object]$CheckInfo)

    $checkContent = Get-Content $CheckInfo.Path -Raw

    # Check for multi-service usage first
    $hasGraph = $checkContent -match 'Get-Mg|Invoke-MgGraphRequest|Update-Mg|New-Mg|Remove-Mg'
    $hasExchange = $checkContent -match 'Get-EXO|Get-Malware|Get-AntiPhish|Get-Hosted|Get-Dkim|Get-AcceptedDomain'
    $hasTeams = $checkContent -match 'Get-Cs|Set-Cs|New-Cs|Remove-Cs'

    # CRITICAL: Exchange + Graph cannot coexist due to assembly conflicts
    # If check uses both, assign to Graph batch and let it fail with clear error
    # User will need to manually handle or split these checks
    if ($hasGraph -and $hasExchange) {
        Write-Warning "Check $($CheckInfo.CheckId) uses BOTH Graph and Exchange - assigned to Graph batch (Exchange cmdlets will FAIL)"
        return "Graph"
    }

    # If check uses Graph + Teams, assign to Teams batch (will fail)
    if ($hasGraph -and $hasTeams) {
        Write-Warning "Check $($CheckInfo.CheckId) uses both Graph and Teams - this will FAIL"
        return "Teams"
    }

    # If check uses Exchange + Teams, assign to Exchange batch (will fail)
    if ($hasExchange -and $hasTeams) {
        Write-Warning "Check $($CheckInfo.CheckId) uses both Exchange and Teams - this will FAIL"
        return "Exchange"
    }

    # Single-service checks
    if ($hasTeams) {
        return "Teams"
    }

    if ($hasGraph) {
        return "Graph"
    }

    if ($hasExchange) {
        return "Exchange"
    }

    # Default to Exchange batch (includes Compliance, SharePoint, Power BI)
    return "Exchange"
}

# Execute checks in an isolated PowerShell process (batch isolation strategy)
function Invoke-CheckBatch {
    param(
        [Parameter(Mandatory)]
        [array]$Checks,

        [Parameter(Mandatory)]
        [string]$BatchName,

        [Parameter(Mandatory)]
        [hashtable]$AuthParams,

        [Parameter(Mandatory)]
        [string]$Tech,

        [Parameter(Mandatory)]
        [int]$StartingCheckNumber,

        [Parameter(Mandatory)]
        [int]$TotalChecks,

        [switch]$WhatIf
    )

    Write-Log "========================================" -Level "Info"
    Write-Log "Starting Batch: $BatchName ($($Checks.Count) checks)" -Level "Info"
    Write-Log "========================================" -Level "Info"

    # Create a temporary directory for batch execution files
    $tempRoot = if ($env:TEMP) { $env:TEMP } elseif ($env:TMPDIR) { $env:TMPDIR } else { [System.IO.Path]::GetTempPath() }
    $tempDir = Join-Path $tempRoot "M365_Batch_$BatchName_$(Get-Date -Format 'yyyyMMddHHmmss')"
    New-Item -Path $tempDir -ItemType Directory -Force | Out-Null

    try {
        # Write checks data to temp file
        $checksFile = Join-Path $tempDir "checks.json"
        $Checks | ConvertTo-Json -Depth 5 | Set-Content -Path $checksFile -Encoding UTF8

        # Write auth params to temp file
        $authFile = Join-Path $tempDir "auth.json"
        $AuthParams | ConvertTo-Json -Depth 5 | Set-Content -Path $authFile -Encoding UTF8

        # Create batch execution script file with progress tracking
        $batchScriptContent = @"
`$ErrorActionPreference = 'Stop'
`$Checks = Get-Content '$checksFile' -Raw | ConvertFrom-Json
`$AuthParams = Get-Content '$authFile' -Raw | ConvertFrom-Json -AsHashtable

# Progress tracking variables
`$ScanId = '$script:ScanId'
`$ProgressCallbackUrl = '$script:ProgressCallbackUrl'
`$StartingCheckNumber = $StartingCheckNumber
`$TotalChecks = $TotalChecks

# Define progress update function
function Send-ProgressUpdate {
    param(
        [string]`$Status,
        [int]`$CurrentCheck,
        [int]`$TotalChecks,
        [string]`$CheckId = "",
        [string]`$Message = ""
    )

    if (-not `$ProgressCallbackUrl) { return }

    try {
        `$progressData = @{
            scan_id = `$ScanId
            progress_percentage = if (`$TotalChecks -gt 0) { [int][math]::Round((`$CurrentCheck / `$TotalChecks) * 100) } else { 0 }
            current_check = if (`$CheckId) { `$CheckId } else { `$null }
            status = `$Status
            total_checks = `$TotalChecks
        }
        `$jsonPayload = `$progressData | ConvertTo-Json -Compress
        Invoke-RestMethod -Uri `$ProgressCallbackUrl -Method POST -Body `$jsonPayload -ContentType "application/json" -TimeoutSec 3 -ErrorAction SilentlyContinue
    }
    catch {
        # Silently continue if progress updates fail
    }
}

. '$PSScriptRoot\Connect-$Tech.ps1'
Write-Information "[$BatchName] Authenticating..." -InformationAction Continue
`$connectParams = `$AuthParams.Clone()
if (`$AuthParams.TenantDomain) { `$connectParams['Organization'] = `$AuthParams.TenantDomain }
switch ('$BatchName') {
    'Exchange' { `$connectParams['SkipGraph'] = `$true; `$connectParams['SkipTeams'] = `$true }
    'Graph' { `$connectParams['SkipExchange'] = `$true; `$connectParams['SkipTeams'] = `$true }
    'Teams' { `$connectParams['SkipExchange'] = `$true; `$connectParams['SkipGraph'] = `$true }
}
`$authResult = Connect-M365 @connectParams
if (`$authResult.Status -ne 'Success') { throw "Auth failed: `$(`$authResult.Error)" }
Write-Information "[$BatchName] Authenticated" -InformationAction Continue
`$results = @()
`$checkIndex = 0
foreach (`$check in `$Checks) {
    `$r = @{TechType='$Tech'; TenantId=`$AuthParams.TenantId; CheckId=`$check.CheckId; Category=`$check.Category; Status='Unknown'; StartTime=[datetime]::UtcNow; EndTime=`$null; Duration=0; Details=@(); Error=`$null; Metadata=`$check.Metadata}
    try {
        Write-Information "[$BatchName] `$(`$check.CheckId)..." -InformationAction Continue
        `$scriptResult = & `$check.Path
        `$r.EndTime = [datetime]::UtcNow
        `$r.Duration = (`$r.EndTime - `$r.StartTime).TotalSeconds
        if (`$scriptResult -is [hashtable]) {
            `$r.Status = `$scriptResult.status
            `$r.Details = `$scriptResult.details
            if (`$scriptResult.error) { `$r.Error = `$scriptResult.error }
        }
        Write-Information " `$(`$r.Status)" -InformationAction Continue
    } catch {
        `$r.EndTime = [datetime]::UtcNow
        `$r.Duration = (`$r.EndTime - `$r.StartTime).TotalSeconds
        `$r.Status = 'Error'
        `$r.Error = `$_.Exception.Message
        Write-Information " Error" -InformationAction Continue
    }
    `$results += `$r

    # Send progress update after each check
    `$checkIndex++
    `$currentCheckNum = `$StartingCheckNumber + `$checkIndex
    Send-ProgressUpdate -Status "Running" -CurrentCheck `$currentCheckNum -TotalChecks `$TotalChecks -CheckId `$check.CheckId -Message "[$BatchName] `$(`$check.CheckId)"
}
`$results | ConvertTo-Json -Depth 10 | Set-Content -Path '$tempDir\results.json' -Encoding UTF8
"@

        $batchScriptFile = Join-Path $tempDir "batch.ps1"
        $batchScriptContent | Set-Content -Path $batchScriptFile -Encoding UTF8

        # Execute batch script
        $process = Start-Process -FilePath "pwsh" `
                                 -ArgumentList "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $batchScriptFile `
                                 -NoNewWindow -Wait -PassThru

        if ($process.ExitCode -ne 0) {
            throw "Batch exited with code $($process.ExitCode)"
        }

        # Read results
        $resultsFile = Join-Path $tempDir "results.json"
        if (-not (Test-Path $resultsFile)) {
            throw "Results file not found"
        }

        $batchResults = Get-Content $resultsFile -Raw | ConvertFrom-Json
        Write-Log "Batch $BatchName completed: $($batchResults.Count) checks" -Level "Info"
        return $batchResults
    }
    catch {
        Write-Log "Batch $BatchName failed: $($_.Exception.Message)" -Level "Error"
        throw
    }
    finally {
        if (Test-Path $tempDir) {
            Remove-Item -Path $tempDir -Recurse -Force -ErrorAction SilentlyContinue
        }
    }
}

# Execute a single compliance check (legacy method - now used only as fallback)
function Invoke-ComplianceCheck {
    param([object]$CheckInfo)

    $result = @{
        TechType = $script:DetectedTechType
        TenantId = $AuthParams.TenantId
        CheckId = $CheckInfo.CheckId
        Category = $CheckInfo.Category
        Status = "Unknown"
        StartTime = [datetime]::UtcNow
        EndTime = $null
        Duration = 0
        Details = @()
        Error = $null
    }

    try {
        Write-Log "Executing check: $($CheckInfo.CheckId)"

        if ($WhatIf) {
            $result.Status = "Skipped (WhatIf)"
            Write-Log "WhatIf: Would execute check $($CheckInfo.CheckId)"
            return $result
        }

        # Execute the check script
        $scriptResult = & $CheckInfo.Path

        $result.EndTime = [datetime]::UtcNow
        $result.Duration = ($result.EndTime - $result.StartTime).TotalSeconds

        # Parse result
        if ($scriptResult -is [hashtable]) {
            $result.Status = $scriptResult.status
            $result.Details = $scriptResult.details
            if ($scriptResult.error) {
                $result.Error = $scriptResult.error
            }
        } else {
            $result.Status = "Error"
            $result.Error = "Unexpected return format from check script"
        }

        Write-Log "Check $($CheckInfo.CheckId) completed: $($result.Status)"
    }
    catch {
        $result.EndTime = [datetime]::UtcNow
        $result.Duration = ($result.EndTime - $result.StartTime).TotalSeconds
        $result.Status = "Error"
        $result.Error = $_.Exception.Message
        Write-Log "Check $($CheckInfo.CheckId) failed: $($_.Exception.Message)" -Level "Error"
    }

    return $result
}

# Save results to file
function Save-Results {
    param([array]$Results, [string]$OutputPath, [string]$Format)

    if ([string]::IsNullOrWhiteSpace($OutputPath)) {
        Write-Log "No output path provided - returning results in-memory only"
        return
    }

    $outputDir = Split-Path $OutputPath -Parent
    if (-not (Test-Path $outputDir)) {
        New-Item -Path $outputDir -ItemType Directory -Force | Out-Null
    }

    switch ($Format.ToLower()) {
        "json" {
            $Results | ConvertTo-Json -Depth 10 | Set-Content -Path $OutputPath -Encoding UTF8
        }
        "csv" {
            $Results | Export-Csv -Path $OutputPath -NoTypeInformation -Encoding UTF8
        }
    }

    Write-Log "Results saved to: $OutputPath"
}

# Initialize script-level variables
$script:DetectedTechType = $null
$script:AuthResult = $null

# MAIN EXECUTION
try {
    Write-Log "Starting Generic CIS Compliance Check"
    Write-Log "=== Script Parameters Debug ==="
    Write-Log "Tech: '$Tech'"
    Write-Log "AuthParams keys: $($AuthParams.Keys -join ', ')"
    Write-Log "UseExistingAuth: $UseExistingAuth"
    Write-Log "================================"

    # BATCH ISOLATION MODE: Skip main authentication
    # Each batch will authenticate independently in its own isolated process
    Write-Log "Using batch isolation mode - authentication will occur per batch"

    # Detect tech type from available auth scripts
    $authScripts = Get-ChildItem -Path $PSScriptRoot -Filter "Connect-*.ps1"
    if ($authScripts.Count -gt 0) {
        $script:DetectedTechType = $authScripts[0].BaseName -replace "^Connect-", ""
    } else {
        $script:DetectedTechType = $Tech
    }

    Write-Log "Detected Technology: $($script:DetectedTechType)"

    # Set default output and log paths if not provided
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $tenantIdentifier = if ($AuthParams.TenantId) { $AuthParams.TenantId } else { "unknown" }

    # Initialize log file
    $script:LogPath = Join-Path $PSScriptRoot "logs\compliance_$($script:DetectedTechType)_$($tenantIdentifier)_$timestamp.log"
    $logDir = Split-Path $script:LogPath -Parent
    if (-not (Test-Path $logDir)) {
        New-Item -Path $logDir -ItemType Directory -Force | Out-Null
    }

    Write-Log "Log file initialized: $($script:LogPath)"
    if ($OutputPath) {
        Write-Log "Results will be saved to: $OutputPath"
    } else {
        Write-Log "No output path provided - results will be returned in-memory"
    }

    # Get compliance checks
    Send-ProgressUpdate -Status "Initializing" -CurrentCheck 0 -TotalChecks 1 -Message "Loading compliance checks"
    $checks = Get-ComplianceChecks -TechType $script:DetectedTechType -CheckIds $CheckIds -L1Only $L1Only

    if ($checks.Count -eq 0) {
        throw "No compliance checks found"
    }

    # Group checks by service dependency (batch isolation strategy)
    Write-Log "Categorizing checks by service dependency..."
    $exchangeBatchChecks = @()
    $graphBatchChecks = @()
    $teamsBatchChecks = @()

    foreach ($check in $checks) {
        $category = Get-CheckServiceCategory -CheckInfo $check
        switch ($category) {
            "Teams" { $teamsBatchChecks += $check }
            "Graph" { $graphBatchChecks += $check }
            "Exchange" { $exchangeBatchChecks += $check }
        }
    }

    Write-Log "Check distribution:"
    Write-Log "  - Exchange Batch (Exchange/Compliance/SharePoint/PowerBI): $($exchangeBatchChecks.Count) checks"
    Write-Log "  - Graph Batch: $($graphBatchChecks.Count) checks"
    Write-Log "  - Teams Batch: $($teamsBatchChecks.Count) checks"
    Write-Log "  - Total: $($checks.Count) checks"
    Write-Log ""

    # Execute checks in isolated batches
    $results = @()
    $totalChecks = $checks.Count
    $currentCheck = 0

    Write-Log "Executing $totalChecks compliance checks in 3 isolated batches..."
    Write-Log "NOTE: Each batch runs in a separate PowerShell process to avoid assembly conflicts"
    Write-Log ""

    # BATCH 1: Exchange (includes Compliance, SharePoint, Power BI)
    if ($exchangeBatchChecks.Count -gt 0) {
        Write-Progress -Activity "$($script:DetectedTechType) CIS Compliance Check" `
                      -Status "Batch 1/3: Exchange Group" `
                      -CurrentOperation "Executing $($exchangeBatchChecks.Count) checks" `
                      -PercentComplete 10

        Send-ProgressUpdate -Status "Running" -CurrentCheck $currentCheck -TotalChecks $totalChecks -Message "Executing Exchange batch"

        $batchResults = Invoke-CheckBatch -Checks $exchangeBatchChecks -BatchName "Exchange" -AuthParams $AuthParams -Tech $Tech -StartingCheckNumber $currentCheck -TotalChecks $totalChecks -WhatIf:$WhatIf
        $results += $batchResults
        $currentCheck += $exchangeBatchChecks.Count

        Write-Log ""
        Write-Log "Exchange batch complete: $($batchResults.Count) checks executed"
        Write-Log ""
    }

    # BATCH 2: Graph
    if ($graphBatchChecks.Count -gt 0) {
        Write-Progress -Activity "$($script:DetectedTechType) CIS Compliance Check" `
                      -Status "Batch 2/3: Graph" `
                      -CurrentOperation "Executing $($graphBatchChecks.Count) checks" `
                      -PercentComplete 40

        Send-ProgressUpdate -Status "Running" -CurrentCheck $currentCheck -TotalChecks $totalChecks -Message "Executing Graph batch"

        $batchResults = Invoke-CheckBatch -Checks $graphBatchChecks -BatchName "Graph" -AuthParams $AuthParams -Tech $Tech -StartingCheckNumber $currentCheck -TotalChecks $totalChecks -WhatIf:$WhatIf
        $results += $batchResults
        $currentCheck += $graphBatchChecks.Count

        Write-Log ""
        Write-Log "Graph batch complete: $($batchResults.Count) checks executed"
        Write-Log ""
    }

    # BATCH 3: Teams
    if ($teamsBatchChecks.Count -gt 0) {
        Write-Progress -Activity "$($script:DetectedTechType) CIS Compliance Check" `
                      -Status "Batch 3/3: Teams" `
                      -CurrentOperation "Executing $($teamsBatchChecks.Count) checks" `
                      -PercentComplete 70

        Send-ProgressUpdate -Status "Running" -CurrentCheck $currentCheck -TotalChecks $totalChecks -Message "Executing Teams batch"

        $batchResults = Invoke-CheckBatch -Checks $teamsBatchChecks -BatchName "Teams" -AuthParams $AuthParams -Tech $Tech -StartingCheckNumber $currentCheck -TotalChecks $totalChecks -WhatIf:$WhatIf
        $results += $batchResults
        $currentCheck += $teamsBatchChecks.Count

        Write-Log ""
        Write-Log "Teams batch complete: $($batchResults.Count) checks executed"
        Write-Log ""
    }

    Write-Progress -Activity "$($script:DetectedTechType) CIS Compliance Check" -Completed

    # Save results
    Send-ProgressUpdate -Status "Finalizing" -CurrentCheck $totalChecks -TotalChecks $totalChecks -Message "Saving results"
    if ($OutputPath) {
        Save-Results -Results $results -OutputPath $OutputPath -Format $OutputFormat
    } else {
        Write-Log "Results kept in-memory; skipping Save-Results due to missing OutputPath"
    }

    Write-Log "$($script:DetectedTechType) compliance check completed successfully"
    if ($OutputPath) {
        Write-Log "Results saved to: $OutputPath"
    }

    # Prepare final output for Python integration
    $finalOutput = @{
        Status = "Success"
        TechType = $script:DetectedTechType
        OutputPath = $OutputPath
        ChecksExecuted = $results.Count
        Results = $results
    }

    # Output JSON to stdout for Python to capture
    Write-Output ($finalOutput | ConvertTo-Json -Depth 100)

    # Return results for PowerShell callers
    return $finalOutput
}
catch {
    Write-Log "Execution failed: $($_.Exception.Message)" -Level "Error"

    # Prepare error output for Python integration
    $errorOutput = @{
        Status = "Failed"
        TechType = $script:DetectedTechType
        Error = $_.Exception.Message
        OutputPath = $OutputPath
        Results = @()
    }

    # Output JSON to stdout for Python to capture
    Write-Output ($errorOutput | ConvertTo-Json -Depth 100)

    # Return error for PowerShell callers
    return $errorOutput
}
