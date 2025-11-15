# Control: 7.2.8 - Ensure external sharing is restricted by security group
<# CIS_METADATA_START
{"Description":"External sharing of content can be restricted to specific security groups. This setting is\nglobal, applies to sharing in both SharePoint and OneDrive and cannot be set at the site\nlevel in SharePoint.\nThe recommended state is Enabled or Checked.\nNote: Users in these security groups must be allowed to invite guests in the guest invite\nsettings in Microsoft Entra. Identity > External Identities > External collaboration settings","Impact":"OneDrive will also be governed by this and there is no granular control at the\nSharePoint site level.","Audit":"To audit using the UI:\n1. Navigate to SharePoint admin center https://admin.microsoft.com/sharepoint\n2. Click to expand Policies > Sharing.\n3. Scroll to and expand More external sharing settings.\n4. Ensure the following:\no Verify Allow only users in specific security groups to share\nexternally is checked\no Verify Manage security groups is defined and accordance with\ncompany procedure.","Remediation":"To remediate using the UI:\n1. Navigate to SharePoint admin center https://admin.microsoft.com/sharepoint\n2. Click to expand Policies > Sharing.\n3. Scroll to and expand More external sharing settings.\n4. Set the following:\no Check Allow only users in specific security groups to share\nexternally\no Define Manage security groups in accordance with company\nprocedure.","Title":"Ensure external sharing is restricted by security group","ProfileApplicability":"- E3 Level 2\n- E5 Level 2","SubSection":"7.2 Policies","DefaultValue":"Unchecked/Undefined","Level":"L2","CISControls":"[{\"version\": \"\", \"id\": \"6.8\", \"title\": \"Define and Maintain Role-Based Access Control\", \"description\": \"Define and maintain role-based access control, through determining and v8 documenting the access rights necessary for each role within the enterprise to - successfully carry out its assigned duties. Perform access control reviews of enterprise assets to validate that all privileges are authorized, on a recurring schedule at a minimum annually, or more frequently.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]","References":"1. https://learn.microsoft.com/en-us/sharepoint/manage-security-groups","Rationale":"Organizations wishing to create tighter security controls for external sharing can set this\nto enforce role-based access control by using security groups already defined in\nMicrosoft Entra.","Section":"7 SharePoint admin center","RecommendationId":"7.2.8"}
CIS_METADATA_END #>
# Required Services: SharePoint
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()

    # Retrieve SharePoint sharing settings
    $sharingSettings = Get-PnPTenantSite -Identity "https://yourtenant-admin.sharepoint.com" | Select-Object -ExpandProperty SharingCapability

    # Check if external sharing is restricted by security group
    $isRestrictedBySecurityGroup = $false
    if ($sharingSettings -eq "ExistingExternalUserSharingOnly") {
        $isRestrictedBySecurityGroup = $true
    }

    # Add result to the results array
    $resourceResults += @{
        ResourceName = "SharePoint External Sharing"
        CurrentValue = $sharingSettings
        IsCompliant = $isRestrictedBySecurityGroup
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
