# Control: 7.2.3 - Ensure external content sharing is restricted
<# CIS_METADATA_START
{"Description":"The external sharing settings govern sharing for the organization overall. Each site has\nits own sharing setting that can be set independently, though it must be at the same or\nmore restrictive setting as the organization.\nThe new and existing guests option requires people who have received invitations to\nsign in with their work or school account (if their organization uses Microsoft 365) or a\nMicrosoft account, or to provide a code to verify their identity. Users can share with\nguests already in your organization's directory, and they can send invitations to people\nwho will be added to the directory if they sign in.\nThe recommended state is New and existing guests or less permissive.","Impact":"When using B2B integration, Entra ID external collaboration settings, such as guest\ninvite settings and collaboration restrictions apply.","Audit":"To audit using the UI:\n1. Navigate to SharePoint admin center https://admin.microsoft.com/sharepoint\n2. Click to expand Policies > Sharing.\n3. Locate the External sharing section.\n4. Under SharePoint, ensure the slider bar is set to New and existing guests or\na less permissive level.\nTo audit using PowerShell:\n1. Connect to SharePoint Online service using Connect-SPOService.\n2. Run the following cmdlet:\nGet-SPOTenant | fl SharingCapability\n3. Ensure SharingCapability is set to one of the following values:\no Value1: ExternalUserSharingOnly\no Value2: ExistingExternalUserSharingOnly\no Value3: Disabled","Remediation":"To remediate using the UI:\n1. Navigate to SharePoint admin center https://admin.microsoft.com/sharepoint\n2. Click to expand Policies > Sharing.\n3. Locate the External sharing section.\n4. Under SharePoint, move the slider bar to New and existing guests or a less\npermissive level.\no OneDrive will also be moved to the same level and can never be more\npermissive than SharePoint.\nTo remediate using PowerShell:\n1. Connect to SharePoint Online service using Connect-SPOService.\n2. Run the following cmdlet to establish the minimum recommended state:\nSet-SPOTenant -SharingCapability ExternalUserSharingOnly\nNote: Other acceptable values for this parameter that are more restrictive include:\nDisabled and ExistingExternalUserSharingOnly.","Title":"Ensure external content sharing is restricted","ProfileApplicability":"- E3 Level 1\n- E5 Level 1","SubSection":"7.2 Policies","DefaultValue":"Anyone (ExternalUserAndGuestSharing)","Level":"L1","CISControls":"[{\"version\": \"\", \"id\": \"3.3\", \"title\": \"Configure Data Access Control Lists\", \"description\": \"v8 Configure data access control lists based on a user's need to know. Apply - - - data access control lists, also known as access permissions, to local and remote file systems, databases, and applications.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]","References":"1. https://learn.microsoft.com/en-us/sharepoint/turn-external-sharing-on-or-off\n2. https://learn.microsoft.com/en-us/powershell/module/sharepoint-online/set-\nspotenant?view=sharepoint-ps","Rationale":"Forcing guest authentication on the organization's tenant enables the implementation of\ncontrols and oversight over external file sharing. When a guest is registered with the\norganization, they now have an identity which can be accounted for. This identity can\nalso have other restrictions applied to it through group membership and conditional\naccess rules.","Section":"7 SharePoint admin center","RecommendationId":"7.2.3"}
CIS_METADATA_END #>
# Required Services: SharePoint
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()
    # Get the current SharingCapability setting using PnP PowerShell
    $tenantSettings = Get-PnPTenant
    $sharingCapability = $tenantSettings.SharingCapability

    # Determine compliance based on SharingCapability
    $isCompliant = $false
    switch ($sharingCapability) {
        'ExternalUserSharingOnly' { $isCompliant = $true }
        'ExistingExternalUserSharingOnly' { $isCompliant = $true }
        'Disabled' { $isCompliant = $true }
        default { $isCompliant = $false }
    }

    # Add result to the results array
    $resourceResults += @{
        Resource = "SharePoint Online Tenant"
        Setting = "SharingCapability"
        CurrentValue = $sharingCapability
        ExpectedValue = "ExternalUserSharingOnly, ExistingExternalUserSharingOnly, or Disabled"
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
