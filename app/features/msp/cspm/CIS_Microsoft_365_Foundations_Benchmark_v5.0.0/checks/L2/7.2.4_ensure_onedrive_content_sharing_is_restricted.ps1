# Control: 7.2.4 - Ensure OneDrive content sharing is restricted
<# CIS_METADATA_START
{"Description":"This setting governs the global permissiveness of OneDrive content sharing in the\norganization.\nOneDrive content sharing can be restricted independent of SharePoint but can never be\nmore permissive than the level established with SharePoint.\nThe recommended state is Only people in your organization.","Impact":"Users will be required to take additional steps to share OneDrive content or use other\nofficial channels.","Audit":"To audit using the UI:\n1. Navigate to SharePoint admin center https://admin.microsoft.com/sharepoint\n2. Click to expand Policies > Sharing.\n3. Locate the External sharing section.\n4. Under OneDrive, ensure the slider bar is set to Only people in your\norganization.\nTo audit using PowerShell:\n1. Connect to SharePoint Online service using Connect-SPOService.\n2. Run the following cmdlet:\nGet-SPOTenant | fl OneDriveSharingCapability\n3. Ensure the returned value is Disabled.\nAlternative audit method using PowerShell:\n1. Connect to SharePoint Online.\n2. Use one of the following methods:\n# Replace [tenant] with your tenant id\nGet-SPOSite -Identity https://[tenant]-my.sharepoint.com/ | fl\nUrl,SharingCapability\n# Or run this to filter to the specific site without supplying the tenant\nname.\n$OneDriveSite = Get-SPOSite -Filter { Url -like \"*-my.sharepoint.com/\" }\nGet-SPOSite -Identity $OneDriveSite | fl Url,SharingCapability\n2. Ensure the returned value for SharingCapability is Disabled\nNote: As of March 2024, using Get-SPOSite with Where-Object or filtering against the\nentire site and then returning the SharingCapability parameter can result in a\ndifferent value as opposed to running the cmdlet specifically against the OneDrive\nspecific site using the -Identity switch as shown in the example.\nNote 2: The parameter OneDriveSharingCapability may not be yet fully available in\nall tenants. It is demonstrated in official Microsoft documentation as linked in the\nreferences section but not in the Set-SPOTenant cmdlet itself. If the parameter is\nunavailable, then either use the UI method or alternative PowerShell audit method.","Remediation":"To remediate using the UI:\n1. Navigate to SharePoint admin center https://admin.microsoft.com/sharepoint\n2. Click to expand Policies > Sharing.\n3. Locate the External sharing section.\n4. Under OneDrive, set the slider bar to Only people in your organization.\nTo remediate using PowerShell:\n1. Connect to SharePoint Online service using Connect-SPOService.\n2. Run the following cmdlet:\nSet-SPOTenant -OneDriveSharingCapability Disabled\nAlternative remediation method using PowerShell:\n1. Connect to SharePoint Online.\n2. Run one of the following:\n# Replace [tenant] with your tenant id\nSet-SPOSite -Identity https://[tenant]-my.sharepoint.com/ -SharingCapability\nDisabled\n# Or run this to filter to the specific site without supplying the tenant\nname.\n$OneDriveSite = Get-SPOSite -Filter { Url -like \"*-my.sharepoint.com/\" }\nSet-SPOSite -Identity $OneDriveSite -SharingCapability Disabled","Title":"Ensure OneDrive content sharing is restricted","ProfileApplicability":"- E3 Level 2\n- E5 Level 2","SubSection":"7.2 Policies","DefaultValue":"Anyone (ExternalUserAndGuestSharing)","Level":"L2","CISControls":"[{\"version\": \"\", \"id\": \"3.3\", \"title\": \"Configure Data Access Control Lists\", \"description\": \"v8 Configure data access control lists based on a user's need to know. Apply - - - data access control lists, also known as access permissions, to local and remote file systems, databases, and applications.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]","References":"1. https://learn.microsoft.com/en-us/powershell/module/sharepoint-online/set-\nspotenant?view=sharepoint-ps#-onedrivesharingcapability","Rationale":"OneDrive, designed for end-user cloud storage, inherently provides less oversight and\ncontrol compared to SharePoint, which often involves additional content overseers or\nsite administrators. This autonomy can lead to potential risks such as inadvertent\nsharing of privileged information by end users. Restricting external OneDrive sharing\nwill require users to transfer content to SharePoint folders first which have those tighter\ncontrols.","Section":"7 SharePoint admin center","RecommendationId":"7.2.4"}
CIS_METADATA_END #>
# Required Services: SharePoint
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()

    # Adapted script logic from the original script
    # Removed Connect-SPOService as authentication is handled centrally

    # Retrieve OneDrive sharing capability
    $tenantSettings = Get-PnPTenant
    $oneDriveSharingCapability = $tenantSettings.OneDriveSharingCapability

    # Retrieve OneDrive site information
    $oneDriveSite = Get-PnPTenantSite -Filter "Url -like '*-my.sharepoint.com/'"
    $siteDetails = Get-PnPTenantSite -Identity $oneDriveSite.Url

    # Analyze compliance based on sharing capability
    $isCompliant = $siteDetails.SharingCapability -eq 'Disabled'

    # Add result to the results array
    $resourceResults += @{
        SiteUrl = $siteDetails.Url
        SharingCapability = $siteDetails.SharingCapability
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
