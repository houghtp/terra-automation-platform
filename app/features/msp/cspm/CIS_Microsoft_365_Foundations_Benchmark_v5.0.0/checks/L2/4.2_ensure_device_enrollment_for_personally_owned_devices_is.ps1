# Control: 4.2 - Ensure device enrollment for personally owned devices is
# Required Services: SecurityCompliance, MgGraph
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()
    
    # Adapted script logic from the original script
    $Uri = 'https://graph.microsoft.com/v1.0/deviceManagement/deviceEnrollmentConfigurations'
    $Config = (Invoke-MgGraphRequest -Uri $Uri -Method GET).value | Where-Object { $_.id -match 'DefaultPlatformRestrictions' -and $_.priority -eq 0 }
    
    # Process each configuration and determine compliance
    foreach ($configItem in $Config) {
        $isCompliant = $true
        
        # Check platform restrictions
        if ($configItem.windowsMobileRestriction -ne $true -or 
            $configItem.macOSRestriction -ne $true -or 
            $configItem.androidRestriction -ne $true) {
            $isCompliant = $false
        }
        
        # Check if platform is blocked
        if ($configItem.platformBlocked -eq $true) {
            $isCompliant = $true
        }
        
        # Add result to the results array
        $resourceResults += @{
            Id = $configItem.id
            Name = $configItem.displayName
            IsCompliant = $isCompliant
            Details = @{
                WindowsMobileRestriction = $configItem.windowsMobileRestriction
                MacOSRestriction = $configItem.macOSRestriction
                AndroidRestriction = $configItem.androidRestriction
                PlatformBlocked = $configItem.platformBlocked
            }
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
