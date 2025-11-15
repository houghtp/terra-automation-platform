# Control: 4.1 - Ensure devices without a compliance policy are marked
# Required Services: SecurityCompliance, MgGraph
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()
    # Define the URI for the device management settings
    $Uri = 'https://graph.microsoft.com/v1.0/deviceManagement/settings'
    
    # Invoke the request to get device management settings
    $response = Invoke-MgGraphRequest -Uri $Uri -Method GET
    
    # Process the response and populate the results array
    foreach ($setting in $response.value) {
        $resourceResults += [PSCustomObject]@{
            Name        = $setting.displayName
            IsCompliant = $setting.isCompliant
        }
    }
    
    # Determine overall status
    $overallStatus = if (($resourceResults | Where-Object { -not $_.IsCompliant })) { 'Fail' } else { 'Pass' }
    $status_id = if ($overallStatus -eq 'Pass') { 1 } else { 3 }
    
    return @{
        status = $overallStatus
        status_id = $status_id
        Details = $resourceResults
    }
}
catch {
    Write-Error "Script execution failed: $($_.Exception.Message)"
    return @{
        status = "Error"
        status_id = 3
        Details = @()
        Error = $_.Exception.Message
    }
}
