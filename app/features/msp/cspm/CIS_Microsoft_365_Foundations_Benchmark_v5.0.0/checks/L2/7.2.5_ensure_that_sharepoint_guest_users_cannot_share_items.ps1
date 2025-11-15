# Control: 7.2.5 - Ensure that SharePoint guest users cannot share items
<# CIS_METADATA_START
{"Description":"SharePoint gives users the ability to share files, folders, and site collections. Internal\nusers can share with external collaborators, and with the right permissions could share\nto other external parties.","Impact":"The impact associated with this change is highly dependent upon current practices. If\nusers do not regularly share with external parties, then minimal impact is likely.\nHowever, if users do regularly share with guests/externally, minimum impacts could\noccur as those external users will be unable to 're-share' content.","Audit":"To audit using the UI:\n1. Navigate to SharePoint admin center https://admin.microsoft.com/sharepoint\n2. Click to expand Policies then select Sharing.\n3. Expand More external sharing settings, verify that Allow guests to\nshare items they don't own is unchecked.\nTo audit using PowerShell:\n1. Connect to SharePoint Online service using Connect-SPOService.\n2. Run the following SharePoint Online PowerShell command:\nGet-SPOTenant | ft PreventExternalUsersFromResharing\n3. Ensure the returned value is True.","Remediation":"To remediate using the UI:\n1. Navigate to SharePoint admin center https://admin.microsoft.com/sharepoint\n2. Click to expand Policies then select Sharing.\n3. Expand More external sharing settings, uncheck Allow guests to\nshare items they don't own.\n4. Click Save.\nTo remediate using PowerShell:\n1. Connect to SharePoint Online service using Connect-SPOService.\n2. Run the following SharePoint Online PowerShell command:\nSet-SPOTenant -PreventExternalUsersFromResharing $True","Title":"Ensure that SharePoint guest users cannot share items","ProfileApplicability":"- E3 Level 2\n- E5 Level 2","SubSection":"7.2 Policies","DefaultValue":"Checked (False)","Level":"L2","CISControls":"[{\"version\": \"\", \"id\": \"3.3\", \"title\": \"Configure Data Access Control Lists\", \"description\": \"v8 Configure data access control lists based on a user's need to know. Apply data - - - access control lists, also known as access permissions, to local and remote file systems, databases, and applications.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"\", \"id\": \"14.6\", \"title\": \"Protect Information through Access Control Lists\", \"description\": \"Protect all information stored on systems with file system, network share, v7 claims, application, or database specific access control lists. These controls will - - - enforce the principle that only authorized individuals should have access to the information based on their need to access the information as a part of their responsibilities.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]","References":"1. https://learn.microsoft.com/en-us/sharepoint/turn-external-sharing-on-or-off\n2. https://learn.microsoft.com/en-us/sharepoint/external-sharing-overview","Rationale":"Sharing and collaboration are key; however, file, folder, or site collection owners should\nhave the authority over what external users get shared with to prevent unauthorized\ndisclosures of information.","Section":"7 SharePoint admin center","RecommendationId":"7.2.5"}
CIS_METADATA_END #>
# Required Services: PnP PowerShell (Linux compatible)
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()

    # Use PnP PowerShell instead of SharePoint Online PowerShell (Linux compatible)
    $tenantSettings = Get-PnPTenant

    # Check the PreventExternalUsersFromResharing setting
    $isCompliant = $tenantSettings.PreventExternalUsersFromResharing -eq $true

    # Add the result to the results array
    $resourceResults += @{
        Setting = "PreventExternalUsersFromResharing"
        IsCompliant = $isCompliant
        CurrentValue = $tenantSettings.PreventExternalUsersFromResharing
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
