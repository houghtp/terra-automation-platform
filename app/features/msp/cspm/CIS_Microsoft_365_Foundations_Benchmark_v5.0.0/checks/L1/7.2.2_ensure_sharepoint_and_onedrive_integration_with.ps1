# Control: 7.2.2 - Ensure SharePoint and OneDrive integration with
<# CIS_METADATA_START
{"Description": "Entra ID B2B provides authentication and management of guests. Authentication\nhappens via one-time passcode when they don't already have a work or school account\nor a Microsoft account. Integration with SharePoint and OneDrive allows for more\ngranular control of how guest user accounts are managed in the organization's AAD,\nunifying a similar guest experience already deployed in other Microsoft 365 services\nsuch as Teams.\nNote: Global Reader role currently can't access SharePoint using PowerShell.", "Impact": "B2B collaboration is used with other Entra services so should not be new or unusual.\nMicrosoft also has made the experience seamless when turning on integration on\nSharePoint sites that already have active files shared with guest users. The referenced\nMicrosoft article on the subject has more details on this.", "Audit": "To audit using PowerShell:\n1. Connect to SharePoint Online using Connect-SPOService\n2. Run the following command:\nGet-SPOTenant | ft EnableAzureADB2BIntegration\n3. Ensure the returned value is True.", "Remediation": "To remediate using PowerShell:\n1. Connect to SharePoint Online using Connect-SPOService\n2. Run the following command:\nSet-SPOTenant -EnableAzureADB2BIntegration $true", "Title": "Ensure SharePoint and OneDrive integration with Azure AD B2B is enabled", "ProfileApplicability": "- E3 Level 1\n- E5 Level 1", "SubSection": "7.2 Policies", "DefaultValue": "False", "Level": "L1", "CISControls": "[{\"version\": \"v8\", \"id\": \"0.0\", \"title\": \"Explicitly Not Mapped\", \"description\": \"Explicitly Not Mapped\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]", "References": "1. https://learn.microsoft.com/en-us/sharepoint/sharepoint-azureb2b-\nintegration#enabling-the-integration\n2. https://learn.microsoft.com/en-us/entra/external-id/what-is-b2b\n3. https://learn.microsoft.com/en-us/powershell/module/sharepoint-online/set-\nspotenant?view=sharepoint-ps", "Rationale": "External users assigned guest accounts will be subject to Entra ID access policies, such\nas multi-factor authentication. This provides a way to manage guest identities and\ncontrol access to SharePoint and OneDrive resources. Without this integration, files can\nbe shared without account registration, making it more challenging to audit and manage\nwho has access to the organization's data.", "Section": "7 SharePoint admin center", "RecommendationId": "7.2.2"}
CIS_METADATA_END #>
# Required Services: PnP PowerShell (Linux compatible)
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()

    # Use PnP PowerShell instead of SharePoint Online PowerShell (Linux compatible)
    $tenantSettings = Get-PnPTenant

    # Check the EnableAzureADB2BIntegration setting
    $isCompliant = $tenantSettings.EnableAzureADB2BIntegration -eq $true

    # Add the result to the results array
    $resourceResults += @{
        Setting = "EnableAzureADB2BIntegration"
        IsCompliant = $isCompliant
        CurrentValue = $tenantSettings.EnableAzureADB2BIntegration
        ExpectedValue = $true
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
