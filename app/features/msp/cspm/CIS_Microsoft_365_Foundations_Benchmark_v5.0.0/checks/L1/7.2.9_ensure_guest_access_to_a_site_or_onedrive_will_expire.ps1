# Control: 7.2.9 - Ensure guest access to a site or OneDrive will expire
<# CIS_METADATA_START
{"Description":"This policy setting configures the expiration time for each guest that is invited to the\nSharePoint site or with whom users share individual files and folders with.\nThe recommended state is 30 or less.","Impact":"Site collection administrators will have to renew access to guests who still need access\nafter 30 days. They will receive an e-mail notification once per week about guest access\nthat is about to expire.\nNote: The guest expiration policy only applies to guests who use sharing links or guests\nwho have direct permissions to a SharePoint site after the guest policy is enabled. The\nguest policy does not apply to guest users that have pre-existing permissions or access\nthrough a sharing link before the guest expiration policy is applied.","Audit":"To audit using the UI:\n1. Navigate to SharePoint admin center https://admin.microsoft.com/sharepoint\n2. Click to expand Policies > Sharing.\n3. Scroll to and expand More external sharing settings.\n4. Ensure Guest access to a site or OneDrive will expire\nautomatically after this many days is checked and set to 30 or less.\nTo audit using PowerShell:\n1. Connect to SharePoint Online service using Connect-SPOService.\n2. Run the following cmdlet:\nGet-SPOTenant | fl ExternalUserExpirationRequired,ExternalUserExpireInDays\n3. Ensure the following values are returned:\no ExternalUserExpirationRequired is True.\no ExternalUserExpireInDays is 30 or less.","Remediation":"To remediate using the UI:\n1. Navigate to SharePoint admin center https://admin.microsoft.com/sharepoint\n2. Click to expand Policies > Sharing.\n3. Scroll to and expand More external sharing settings.\n4. Set Guest access to a site or OneDrive will expire automatically\nafter this many days to 30\nTo remediate using PowerShell:\n1. Connect to SharePoint Online service using Connect-SPOService.\n2. Run the following cmdlet:\nSet-SPOTenant -ExternalUserExpireInDays 30 -ExternalUserExpirationRequired\n$True","Title":"Ensure guest access to a site or OneDrive will expire","ProfileApplicability":"- E3 Level 1\n- E5 Level 1","SubSection":"7.2 Policies","DefaultValue":"ExternalUserExpirationRequired $false\nExternalUserExpireInDays 60 days","Level":"L1","CISControls":"[{\"version\": \"v8\", \"id\": \"0.0\", \"title\": \"Explicitly Not Mapped\", \"description\": \"Explicitly Not Mapped\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"v7\", \"id\": \"0.0\", \"title\": \"Explicitly Not Mapped\", \"description\": \"Explicitly Not Mapped\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]","References":"1. https://learn.microsoft.com/en-us/sharepoint/turn-external-sharing-on-or-\noff#change-the-organization-level-external-sharing-setting\n2. https://learn.microsoft.com/en-us/microsoft-365/community/sharepoint-security-a-\nteam-effort","Rationale":"This setting ensures that guests who no longer need access to the site or link no longer\nhave access after a set period of time. Allowing guest access for an indefinite amount of\ntime could lead to loss of data confidentiality and oversight.\nNote: Guest membership applies at the Microsoft 365 group level. Guests who have\npermission to view a SharePoint site or use a sharing link may also have access to a\nMicrosoft Teams team or security group.","Section":"7 SharePoint admin center","RecommendationId":"7.2.9"}
CIS_METADATA_END #>
# Required Services: SharePoint
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()
    # Execute the original logic to check tenant settings
        # Get SharePoint tenant settings using PnP PowerShell
    $tenantSettings = Get-PnPTenant
    $externalUserExpirationRequired = $tenantSettings.ExternalUserExpirationRequired
    $externalUserExpireInDays = $tenantSettings.ExternalUserExpireInDays

    # Evaluate compliance
    $isCompliant = $externalUserExpirationRequired -eq $true -and $externalUserExpireInDays -le 30

    # Add result to the results array
    $resourceResults += @{
        Setting = "ExternalUserExpirationRequired"
        Value = $externalUserExpirationRequired
        IsCompliant = $externalUserExpirationRequired -eq $true
    }

    $resourceResults += @{
        Setting = "ExternalUserExpireInDays"
        Value = $externalUserExpireInDays
        IsCompliant = $externalUserExpireInDays -le 30
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
