# Control: 7.2.1 - Ensure modern authentication for SharePoint
<# CIS_METADATA_START
{"Description":"Modern authentication in Microsoft 365 enables authentication features like multifactor\nauthentication (MFA) using smart cards, certificate-based authentication (CBA), and\nthird-party SAML identity providers.","Impact":"Implementation of modern authentication for SharePoint will require users to\nauthenticate to SharePoint using modern authentication. This may cause a minor\nimpact to typical user behavior.\nThis may also prevent third-party apps from accessing SharePoint Online resources.\nAlso, this will also block apps using the SharePointOnlineCredentials class to access\nSharePoint Online resources.","Audit":"To audit using the UI:\n1. Navigate to SharePoint admin center https://admin.microsoft.com/sharepoint.\n2. Click to expand Policies select Access control.\n3. Select Apps that don't use modern authentication and ensure that it is\nset to Block access.\nTo audit using PowerShell:\n1. Connect to SharePoint Online using Connect-SPOService -Url\nhttps://tenant-admin.sharepoint.com replacing tenant with your value.\n2. Run the following SharePoint Online PowerShell command:\nGet-SPOTenant | ft LegacyAuthProtocolsEnabled\n3. Ensure the returned value is False.","Remediation":"To remediate using the UI:\n1. Navigate to SharePoint admin center https://admin.microsoft.com/sharepoint.\n2. Click to expand Policies select Access control.\n3. Select Apps that don't use modern authentication.\n4. Select the radio button for Block access.\n5. Click Save.\nTo remediate using PowerShell:\n1. Connect to SharePoint Online using Connect-SPOService -Url\nhttps://tenant-admin.sharepoint.com replacing tenant with your value.\n2. Run the following SharePoint Online PowerShell command:\nSet-SPOTenant -LegacyAuthProtocolsEnabled $false","Title":"Ensure modern authentication for SharePoint","ProfileApplicability":"- E3 Level 1\n- E5 Level 1","SubSection":"7.2 Policies","DefaultValue":"True (Apps that don't use modern authentication are allowed)","Level":"L1","CISControls":"[{\"version\": \"\", \"id\": \"3.10\", \"title\": \"Encrypt Sensitive Data in Transit\", \"description\": \"Encrypt sensitive data in transit. Example implementations can include: - - Transport Layer Security (TLS) and Open Secure Shell (OpenSSH).\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"v8\", \"id\": \"16.3\", \"title\": \"Require Multi-factor Authentication\", \"description\": \"Require multi-factor authentication for all user accounts, on all systems, - - whether managed onsite or by a third-party provider.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]","References":"1. https://learn.microsoft.com/en-us/powershell/module/sharepoint-online/set-\nspotenant?view=sharepoint-ps","Rationale":"Strong authentication controls, such as the use of multifactor authentication, may be\ncircumvented if basic authentication is used by SharePoint applications. Requiring\nmodern authentication for SharePoint applications ensures strong authentication\nmechanisms are used when establishing sessions between these applications,\nSharePoint, and connecting users.","Section":"7 SharePoint admin center","RecommendationId":"7.2.1"}
CIS_METADATA_END #>
# Required Services: PnP PowerShell (Linux compatible)
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()

    # Use PnP PowerShell instead of SharePoint Online PowerShell (Linux compatible)
    $tenantSettings = Get-PnPTenant
    $legacyAuthEnabled = $tenantSettings.LegacyAuthProtocolsEnabled

    # Convert results to standard format
    $resourceResults += @{
        Resource = "SharePoint Online"
        Setting = "LegacyAuthProtocolsEnabled"
        IsCompliant = -not $legacyAuthEnabled
        CurrentValue = $legacyAuthEnabled
        ExpectedValue = $false
        Details = "Legacy authentication protocols should be disabled."
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
