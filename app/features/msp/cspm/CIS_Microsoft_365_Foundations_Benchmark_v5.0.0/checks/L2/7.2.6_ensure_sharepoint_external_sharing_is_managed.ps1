# Control: 7.2.6 - Ensure SharePoint external sharing is managed
<# CIS_METADATA_START
{"Description":"Control sharing of documents to external domains by either blocking domains or only\nallowing sharing with specific named domains.","Impact":"Enabling this feature will prevent users from sharing documents with domains outside of\nthe organization unless allowed.","Audit":"To audit using the UI:\n1. Navigate to SharePoint admin center https://admin.microsoft.com/sharepoint\n2. Expand Policies then click Sharing.\n3. Expand More external sharing settings and confirm that Limit external\nsharing by domain is checked.\n4. Verify that an accurate list of allowed domains is listed.\nTo audit using PowerShell:\n1. Connect to SharePoint Online using Connect-SPOService.\n2. Run the following PowerShell command:\nGet-SPOTenant | fl SharingDomainRestrictionMode,SharingAllowedDomainList\n3. Ensure that SharingDomainRestrictionMode is set to AllowList and\nSharingAllowedDomainList contains domains trusted by the organization for\nexternal sharing.","Remediation":"To remediate using the UI:\n1. Navigate to SharePoint admin center https://admin.microsoft.com/sharepoint.\n2. Expand Policies then click Sharing.\n3. Expand More external sharing settings and check Limit external\nsharing by domain.\n4. Select Add domains to add a list of approved domains.\n5. Click Save at the bottom of the page.\nTo remediate using PowerShell:\n1. Connect to SharePoint Online using Connect-SPOService.\n2. Run the following PowerShell command:\nSet-SPOTenant -SharingDomainRestrictionMode AllowList -\nSharingAllowedDomainList \"domain1.com domain2.com\"","Title":"Ensure SharePoint external sharing is managed","ProfileApplicability":"- E3 Level 2\n- E5 Level 2","SubSection":"7.2 Policies","DefaultValue":"Limit external sharing by domain is unchecked\nSharingDomainRestrictionMode: None\nSharingDomainRestrictionMode: <Undefined>","Level":"L2","CISControls":"[{\"version\": \"\", \"id\": \"3.3\", \"title\": \"Configure Data Access Control Lists\", \"description\": \"v8 Configure data access control lists based on a user's need to know. Apply data - - - access control lists, also known as access permissions, to local and remote file systems, databases, and applications.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"\", \"id\": \"13.4\", \"title\": \"Only Allow Access to Authorized Cloud Storage or\", \"description\": \"v7 Email Providers - - Only allow access to authorized cloud storage or email providers.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"\", \"id\": \"14.6\", \"title\": \"Protect Information through Access Control Lists\", \"description\": \"Protect all information stored on systems with file system, network share, v7 claims, application, or database specific access control lists. These controls will - - - enforce the principle that only authorized individuals should have access to the information based on their need to access the information as a part of their responsibilities.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]","References":"1. https://learn.microsoft.com/en-us/sharepoint/turn-external-sharing-on-or-\noff?WT.mc_id=365AdminCSH_spo#more-external-sharing-settings","Rationale":"Attackers will often attempt to expose sensitive information to external entities through\nsharing, and restricting the domains that users can share documents with will reduce\nthat surface area.","Section":"7 SharePoint admin center","RecommendationId":"7.2.6"}
CIS_METADATA_END #>
# Required Services: PnP PowerShell (Linux compatible)
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()

    # Use PnP PowerShell instead of SharePoint Online PowerShell (Linux compatible)
    $tenantSettings = Get-PnPTenant | Select-Object SharingDomainRestrictionMode, SharingAllowedDomainList

    # Analyze the settings and determine compliance
    $isCompliant = $tenantSettings.SharingDomainRestrictionMode -eq 'None' -or ($tenantSettings.SharingAllowedDomainList -ne $null -and $tenantSettings.SharingAllowedDomainList.Count -gt 0)

    # Add result to the results array
    $resourceResults += @{
        Setting = 'SharingDomainRestrictionMode'
        Value = $tenantSettings.SharingDomainRestrictionMode
        IsCompliant = $isCompliant
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
