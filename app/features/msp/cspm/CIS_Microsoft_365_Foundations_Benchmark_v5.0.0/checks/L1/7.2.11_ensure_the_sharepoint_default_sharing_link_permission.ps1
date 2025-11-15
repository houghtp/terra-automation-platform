# Control: 7.2.11 - Ensure the SharePoint default sharing link permission
<# CIS_METADATA_START
{"Description":"This setting configures the permission that is selected by default for sharing link from a\nSharePoint site.\nThe recommended state is View.","Impact":"Not applicable.","Audit":"To audit using the UI:\n1. Navigate to SharePoint admin center https://admin.microsoft.com/sharepoint\n2. Click to expand Policies > Sharing.\n3. Scroll to File and folder links.\n4. Ensure Choose the permission that's selected by default for\nsharing links is set to View.\nTo audit using PowerShell:\n1. Connect to SharePoint Online service using Connect-SPOService.\n2. Run the following cmdlet:\nGet-SPOTenant | fl DefaultLinkPermission\n3. Ensure the returned value is View.","Remediation":"To remediate using the UI:\n1. Navigate to SharePoint admin center https://admin.microsoft.com/sharepoint\n2. Click to expand Policies > Sharing.\n3. Scroll to File and folder links.\n4. Set Choose the permission that's selected by default for sharing\nlinks to View.\nTo remediate using PowerShell:\n1. Connect to SharePoint Online service using Connect-SPOService.\n2. Run the following cmdlet:\nSet-SPOTenant -DefaultLinkPermission View","Title":"Ensure the SharePoint default sharing link permission","ProfileApplicability":"- E3 Level 1\n- E5 Level 1","SubSection":"7.2 Policies","DefaultValue":"DefaultLinkPermission : Edit","Level":"L1","CISControls":"[{\"version\": \"v8\", \"id\": \"0.0\", \"title\": \"Explicitly Not Mapped\", \"description\": \"Explicitly Not Mapped\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"v7\", \"id\": \"0.0\", \"title\": \"Explicitly Not Mapped\", \"description\": \"Explicitly Not Mapped\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"v7\", \"id\": \"7.3\", \"title\": \"Settings\", \"description\": \"\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]","References":"1. https://learn.microsoft.com/en-us/sharepoint/turn-external-sharing-on-or-off#file-\nand-folder-links","Rationale":"Setting the view permission as the default ensures that users must deliberately select\nthe edit permission when sharing a link. This approach reduces the risk of\nunintentionally granting edit privileges to a resource that only requires read access,\nsupporting the principle of least privilege.","Section":"7 SharePoint admin center","RecommendationId":"7.2.11"}
CIS_METADATA_END #>
# Required Services: PnP PowerShell (Linux compatible)
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()

    # Use PnP PowerShell instead of SharePoint Online PowerShell (Linux compatible)
    $tenantSettings = Get-PnPTenant

    # Extract the DefaultLinkPermission property
    $defaultLinkPermission = $tenantSettings.DefaultLinkPermission

    # Determine compliance based on DefaultLinkPermission
    $isCompliant = $defaultLinkPermission -eq 'View'

    # Add result to the results array
    $resourceResults += @{
        Setting = 'DefaultLinkPermission'
        Value = $defaultLinkPermission
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
