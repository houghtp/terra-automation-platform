# Control: 5.1.2.6 - Ensure 'LinkedIn account connections' is disabled
<# CIS_METADATA_START
{"RecommendationId":"5.1.2.6","Level":"L2","Title":"Ensure 'LinkedIn account connections' is disabled","Section":"5 Microsoft Entra admin center","SubSection":"5.1 Identity","ProfileApplicability":"- E3 Level 2\n- E5 Level 2","Description":"LinkedIn account connections allow users to connect their Microsoft work or school\naccount with LinkedIn. After a user connects their accounts, information and highlights\nfrom LinkedIn are available in some Microsoft apps and services.","Rationale":"Disabling LinkedIn integration prevents potential phishing attacks and risk scenarios\nwhere an external party could accidentally disclose sensitive information.","Impact":"Users will not be able to sync contacts or use LinkedIn integration.","Audit":"To audit using the UI:\n1. Navigate to Microsoft Entra admin center https://entra.microsoft.com/.\n2. Click to expand Identity > Users select User settings.\n3. Under LinkedIn account connections ensure No is highlighted.","Remediation":"To remediate using the UI:\n1. Navigate to Microsoft Entra admin center https://entra.microsoft.com/.\n2. Click to expand Identity > Users select User settings.\n3. Under LinkedIn account connections select No.\n4. Click Save.","DefaultValue":"LinkedIn integration is enabled by default.","References":"1. https://learn.microsoft.com/en-us/entra/identity/users/linkedin-integration\n2. https://learn.microsoft.com/en-us/entra/identity/users/linkedin-user-consent","CISControls":"[{\"version\": \"\", \"id\": \"4.8\", \"title\": \"Uninstall or Disable Unnecessary Services on\", \"description\": \"Enterprise Assets and Software Uninstall or disable unnecessary services on enterprise assets and software, - - such as an unused file sharing service, web application module, or service function.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"v8\", \"id\": \"13.3\", \"title\": \"Monitor and Block Unauthorized Network Traffic\", \"description\": \"v7 Deploy an automated tool on network perimeters that monitors for - unauthorized transfer of sensitive information and blocks such transfers while alerting information security professionals. 5.1.3 Groups\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]"}
CIS_METADATA_END #>
# Required Services: MgGraph
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()
    
    # Retrieve the user settings for LinkedIn account connections
    $userSettings = Get-MgBetaDirectorySetting | Where-Object { $_.DisplayName -eq "LinkedInAccountConnections" }
    
    # Check if LinkedIn account connections are disabled
    if ($userSettings) {
        $currentValue = $userSettings.Values | Where-Object { $_.Name -eq "Enabled" } | Select-Object -ExpandProperty Value
        $isCompliant = $currentValue -eq "False"
        
        $resourceResults += @{
            ResourceName = "LinkedIn Account Connections"
            CurrentValue = $currentValue
            IsCompliant = $isCompliant
        }
    }
    else {
        $resourceResults += @{
            ResourceName = "LinkedIn Account Connections"
            CurrentValue = "Not Found"
            IsCompliant = $false
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
