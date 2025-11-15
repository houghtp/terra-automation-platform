# Control: 8.2.4 - Ensure communication with Skype users is disabled
<# CIS_METADATA_START
{"Description":"This policy setting controls chat with external unmanaged Skype users.\nNote: Starting in May 2025, Skype will no longer be available. This setting will be\nremoved and users won't be able to communicate with Skype users.","Impact":"Teams users will be unable to communicate with Skype users that are not in the same\norganization.","Audit":"To audit using the UI:\n1. Navigate to Microsoft Teams admin center\nhttps://admin.teams.microsoft.com/.\n2. Click to expand Users select External access.\n3. Select the Organization settings tab.\n4. Ensure People in my organization can communicate with Skype users\nis Off.\nTo audit using PowerShell:\n1. Connect to Teams PowerShell using Connect-MicrosoftTeams\n2. Run the following command:\nGet-CsTenantFederationConfiguration | fl AllowPublicUsers\nEnsure AllowPublicUsers is False\nNote: Due to Microsoft's planned removal of this setting in May 2025, if the setting is not\navailable in your tenant, the audit can be considered satisfied. This is because the\nsetting has already been removed, is no longer configurable, and has been permanently\nturned off.","Remediation":"To remediate using the UI:\n1. Navigate to Microsoft Teams admin center\nhttps://admin.teams.microsoft.com/.\n2. Click to expand Users select External access.\n3. Select the Organization settings tab.\n4. Set People in my organization can communicate with Skype users to\nOff.\n5. Click Save.\nTo remediate using PowerShell:\n1. Connect to Teams PowerShell using Connect-MicrosoftTeams\n2. Run the following command:\nSet-CsTenantFederationConfiguration -AllowPublicUsers $false","Title":"Ensure communication with Skype users is disabled","ProfileApplicability":"- E3 Level 1\n- E5 Level 1","SubSection":"8.2 Users","DefaultValue":"- AllowPublicUsers : True","Level":"L1","CISControls":"[{\"version\": \"\", \"id\": \"4.8\", \"title\": \"Uninstall or Disable Unnecessary Services on\", \"description\": \"Enterprise Assets and Software Uninstall or disable unnecessary services on enterprise assets and software, - - such as an unused file sharing service, web application module, or service function.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"v8\", \"id\": \"8.3\", \"title\": \"Teams devices\", \"description\": \"This section is intentionally blank and exists to ensure the structure of the benchmark is consistent.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"v8\", \"id\": \"8.4\", \"title\": \"Teams apps\", \"description\": \"\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]","References":"1. https://learn.microsoft.com/en-us/microsoftteams/trusted-organizations-external-\nmeetings-chat?tabs=organization-settings","Rationale":"Skype was deprecated July 31, 2021. Disabling communication with skype users\nreduces the attack surface of the organization. If a partner organization or satellite office\nwishes to collaborate and has not yet moved off of Skype, then a valid exception will\nneed to be considered for this recommendation.","Section":"8 Microsoft Teams admin center","RecommendationId":"8.2.4"}
CIS_METADATA_END #>
# Required Services: Teams
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()
    # Execute the command to get the tenant federation configuration
    $federationConfig = Get-CsTenantFederationConfiguration
    
    # Check if AllowPublicUsers is set to False
    $isCompliant = -not $federationConfig.AllowPublicUsers
    
    # Add the result to the results array
    $resourceResults += @{
        Name = "AllowPublicUsers"
        IsCompliant = $isCompliant
        CurrentValue = $federationConfig.AllowPublicUsers
        ExpectedValue = $false
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
