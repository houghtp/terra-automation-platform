# Control: 9.1.9 - Ensure 'Block ResourceKey Authentication' is 'Enabled'
<# CIS_METADATA_START
{"Description":"This setting blocks the use of resource key based authentication. The Block\nResourceKey Authentication setting applies to streaming and PUSH datasets. If blocked\nusers will not be allowed to send data to streaming and PUSH datasets using the API\nwith a resource key.\nThe recommended state is Enabled.","Impact":"Developers will need to request a special exception in order to use this feature.","Audit":"To audit using the UI:\n1. Navigate to Microsoft Fabric https://app.powerbi.com/admin-portal\n2. Select Tenant settings.\n3. Scroll to Developer settings.\n4. Ensure that Block ResourceKey Authentication is Enabled","Remediation":"To remediate using the UI:\n1. Navigate to Microsoft Fabric https://app.powerbi.com/admin-portal\n2. Select Tenant settings.\n3. Scroll to Developer settings.\n4. Set Block ResourceKey Authentication to Enabled","Title":"Ensure 'Block ResourceKey Authentication' is 'Enabled'","ProfileApplicability":"- E3 Level 1\n- E5 Level 1","SubSection":"9.1 Tenant settings","DefaultValue":"Disabled for the entire organization","Level":"L1","CISControls":"[{\"version\": \"\", \"id\": \"4.8\", \"title\": \"Uninstall or Disable Unnecessary Services on\", \"description\": \"Enterprise Assets and Software Uninstall or disable unnecessary services on enterprise assets and software, - - such as an unused file sharing service, web application module, or service function.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]","References":"1. https://learn.microsoft.com/en-us/fabric/admin/service-admin-portal-developer\n2. https://learn.microsoft.com/en-us/power-bi/connect-data/service-real-time-\nstreaming","Rationale":"Resource keys are a form of authentication that allows users to access Power BI\nresources (such as reports, dashboards, and datasets) without requiring individual user\naccounts. While convenient, this method bypasses the organization's centralized\nidentity and access management controls. Enabling ensures that access to Power BI\nresources is tied to the organization's authentication mechanisms, providing a more\nsecure and controlled environment.","Section":"9 Microsoft Fabric","RecommendationId":"9.1.9"}
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

    # Check the 'Block ResourceKey Authentication' setting
    $blockResourceKeyAuthSetting = $tenantSettings | Where-Object { $_.settingName -eq "BlockResourceKeyAuthentication" }

    if ($null -ne $blockResourceKeyAuthSetting) {
        $currentValue = if ($blockResourceKeyAuthSetting.enabled) { "Enabled" } else { "Disabled" }
        $isCompliant = $blockResourceKeyAuthSetting.enabled

        $resourceResults += @{
            ResourceName = "Block ResourceKey Authentication"
            CurrentValue = $currentValue
            IsCompliant = $isCompliant
        }
    }
    else {
        throw "Block ResourceKey Authentication setting not found."
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
