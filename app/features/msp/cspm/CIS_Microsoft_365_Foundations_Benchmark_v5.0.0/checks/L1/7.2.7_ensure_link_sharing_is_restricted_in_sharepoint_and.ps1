# Control: 7.2.7 - Ensure link sharing is restricted in SharePoint and
<# CIS_METADATA_START
{"Description":"This setting sets the default link type that a user will see when sharing content in\nOneDrive or SharePoint. It does not restrict or exclude any other options.\nThe recommended state is Specific people (only the people the user\nspecifies) or Only people in your organization (more restrictive).","Impact":"","Audit":"To audit using the UI:\n1. Navigate to SharePoint admin center https://admin.microsoft.com/sharepoint\n2. Click to expand Policies > Sharing.\n3. Scroll to File and folder links.\n4. Ensure that the setting Choose the type of link that's selected by\ndefault when users share files and folders in SharePoint and\nOneDrive is set to Specific people (only the people the user\nspecifies) or Only people in your organization (more restrictive).\nTo audit using PowerShell:\n1. Connect to SharePoint Online using Connect-SPOService.\n2. Run the following PowerShell command:\nGet-SPOTenant | fl DefaultSharingLinkType\n3. Ensure the returned value is Direct or Internal (more restrictive).","Remediation":"To remediate using the UI:\n1. Navigate to SharePoint admin center https://admin.microsoft.com/sharepoint\n2. Click to expand Policies > Sharing.\n3. Scroll to File and folder links.\n4. Set Choose the type of link that's selected by default when users\nshare files and folders in SharePoint and OneDrive to Specific\npeople (only the people the user specifies) or Only people in your\norganization.\nTo remediate using PowerShell:\n1. Connect to SharePoint Online using Connect-SPOService.\n2. Run the following PowerShell command:\nSet-SPOTenant -DefaultSharingLinkType Direct\n3. Or, to set a more restrictive state:\nSet-SPOTenant -DefaultSharingLinkType Internal","Title":"Ensure link sharing is restricted in SharePoint and","ProfileApplicability":"- E3 Level 1\n- E5 Level 1","SubSection":"7.2 Policies","DefaultValue":"Only people in your organization (Internal)","Level":"L1","CISControls":"[{\"version\": \"\", \"id\": \"3.3\", \"title\": \"Configure Data Access Control Lists\", \"description\": \"v8 Configure data access control lists based on a user's need to know. Apply - - - data access control lists, also known as access permissions, to local and remote file systems, databases, and applications.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]","References":"1. https://learn.microsoft.com/en-us/powershell/module/sharepoint-online/set-\nspotenant?view=sharepoint-ps","Rationale":"By defaulting to specific people, the user will first need to consider whether or not the\ncontent being shared should be accessible by the entire organization versus select\nindividuals. This aids in reinforcing the concept of least privilege.","Section":"7 SharePoint admin center","RecommendationId":"7.2.7"}
CIS_METADATA_END #>
# Required Services: PnP PowerShell (Linux compatible)
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()

    # Use PnP PowerShell instead of SharePoint Online PowerShell (Linux compatible)
    $tenantSettings = Get-PnPTenant

    # Analyze the DefaultSharingLinkType setting
    $isCompliant = $tenantSettings.DefaultSharingLinkType -eq 'None'

    # Add result to the results array
    $resourceResults += @{
        Resource = "SharePoint Tenant"
        Setting = "DefaultSharingLinkType"
        CurrentValue = $tenantSettings.DefaultSharingLinkType
        ExpectedValue = "None"
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
