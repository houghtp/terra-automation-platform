# Control: 9.1.7 - Ensure shareable links are restricted
<# CIS_METADATA_START
{"Description":"Creating a shareable link allows a user to create a link to a report or dashboard, then\nadd that link to an email or another messaging application.\nThere are 3 options that can be selected when creating a shareable link:\n- People in your organization\n- People with existing access\n- Specific people\nThis setting solely deals with restrictions to People in the organization. External\nusers by default are not included in any of these categories, and therefore cannot use\nany of these links regardless of the state of this setting.\nThe recommended state is Enabled for a subset of the organization or\nDisabled.","Impact":"If the setting is Enabled then only specific people in the organization would be allowed\nto create general links viewable by the entire organization.","Audit":"To audit using the UI:\n1. Navigate to Microsoft Fabric https://app.powerbi.com/admin-portal\n2. Select Tenant settings.\n3. Scroll to Export and Sharing settings.\n4. Ensure that Allow shareable links to grant access to everyone in\nyour organization adheres to one of these states:\no State 1: Disabled\no State 2: Enabled with Specific security groups selected and defined.\nImportant: If the organization doesn't actively use this feature it is recommended to\nkeep it Disabled.","Remediation":"To remediate using the UI:\n1. Navigate to Microsoft Fabric https://app.powerbi.com/admin-portal\n2. Select Tenant settings.\n3. Scroll to Export and Sharing settings.\n4. Set Allow shareable links to grant access to everyone in your\norganization to one of these states:\no State 1: Disabled\no State 2: Enabled with Specific security groups selected and defined.\nImportant: If the organization doesn't actively use this feature it is recommended to\nkeep it Disabled.","Title":"Ensure shareable links are restricted","ProfileApplicability":"- E3 Level 1\n- E5 Level 1","SubSection":"9.1 Tenant settings","DefaultValue":"Enabled for Entire Organization","Level":"L1","CISControls":"[{\"version\": \"\", \"id\": \"3.3\", \"title\": \"Configure Data Access Control Lists\", \"description\": \"v8 Configure data access control lists based on a user's need to know. Apply - - - data access control lists, also known as access permissions, to local and remote file systems, databases, and applications.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]","References":"1. https://learn.microsoft.com/en-us/power-bi/collaborate-share/service-share-\ndashboards?wt.mc_id=powerbi_inproduct_sharedialog#link-settings\n2. https://learn.microsoft.com/en-us/fabric/admin/service-admin-portal-export-\nsharing","Rationale":"While external users are unable to utilize shareable links, disabling or restricting this\nfeature ensures that a user cannot generate a link accessible by individuals within the\nsame organization who lack the necessary clearance to the shared data. For example,\na member of Human Resources intends to share sensitive information with a particular\nemployee or another colleague within their department. The owner would be prompted\nto specify either People with existing access or Specific people when\ngenerating the link requiring the person clicking the link to pass a first layer access\ncontrol list. This measure along with proper file and folder permissions can help prevent\nunintended access and potential information leakage.","Section":"9 Microsoft Fabric","RecommendationId":"9.1.7"}
CIS_METADATA_END #>
# Required Services: MgGraph
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()

    # Retrieve Power BI tenant settings using user token (hybrid authentication)
    $apiUrl = 'https://api.fabric.microsoft.com/v1/admin/tenantsettings'

    if ($global:PowerBIUserToken) {
        # Use user token for Fabric Admin API (Service Principal doesn't work - returns 500)
        $headers = @{
            "Authorization" = "Bearer $global:PowerBIUserToken"
            "Content-Type"  = "application/json"
        }
        $responseJson = Invoke-RestMethod -Method Get -Uri $apiUrl -Headers $headers -ErrorAction Stop
    } else {
        # Fallback to Power BI session token (Service Principal - may fail with 500 error)
        Write-Warning "No user token available - using Power BI session token (may fail for Fabric Admin API)"
        $responseJson = Invoke-PowerBIRestMethod -Method Get -Url $apiUrl
    }

    $tenantSettings = $responseJson.tenantSettings

    # Check the setting for shareable links
    $shareableLinksSetting = $tenantSettings | Where-Object { $_.settingName -eq "AllowShareableLinksToGrantAccessToEveryoneInYourOrganization" }

    if ($null -ne $shareableLinksSetting) {
        $currentValue = if ($shareableLinksSetting.enabled) { "Enabled" } else { "Disabled" }
        $isCompliant = (-not $shareableLinksSetting.enabled) -or ($shareableLinksSetting.enabled -and $shareableLinksSetting.tenantSettingGroup -ne $null -and $shareableLinksSetting.tenantSettingGroup.Count -gt 0)

        $resourceResults += @{
            ResourceName = "AllowShareableLinksToGrantAccessToEveryoneInYourOrganization"
            CurrentValue = $currentValue
            IsCompliant = $isCompliant
        }
    }
    else {
        $resourceResults += @{
            ResourceName = "AllowShareableLinksToGrantAccessToEveryoneInYourOrganization"
            CurrentValue = "Not Found"
            IsCompliant = $false
        }
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
