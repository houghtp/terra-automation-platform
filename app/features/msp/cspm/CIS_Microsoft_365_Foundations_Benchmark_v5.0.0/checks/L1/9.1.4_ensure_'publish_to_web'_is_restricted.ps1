# Control: 9.1.4 - Ensure 'Publish to web' is restricted
<# CIS_METADATA_START
{"Description":"Power BI enables users to share reports and materials directly on the internet from both\nthe application's desktop version and its web user interface. This functionality generates\na publicly reachable web link that doesn't necessitate authentication or the need to be\nan Entra ID user in order to access and view it.\nThe recommended state is Enabled for a subset of the organization or\nDisabled.","Impact":"Depending on the organization's utilization administrators may experience more\noverhead managing embed codes, and requests.","Audit":"To audit using the UI:\n1. Navigate to Microsoft Fabric https://app.powerbi.com/admin-portal\n2. Select Tenant settings.\n3. Scroll to Export and Sharing settings.\n4. Ensure that Publish to web adheres to one of these states:\no State 1: Disabled\no State 2: Enabled with Choose how embed codes work set to Only\nallow existing codes AND Specific security groups selected and\ndefined\nImportant: If the organization doesn't actively use this feature it is recommended to\nkeep it Disabled.","Remediation":"To remediate using the UI:\n1. Navigate to Microsoft Fabric https://app.powerbi.com/admin-portal\n2. Select Tenant settings.\n3. Scroll to Export and Sharing settings.\n4. Set Publish to web to one of these states:\no State 1: Disabled\no State 2: Enabled with Choose how embed codes work set to Only\nallow existing codes AND Specific security groups selected and\ndefined\nImportant: If the organization doesn't actively use this feature it is recommended to\nkeep it Disabled.","Title":"Ensure 'Publish to web' is restricted","ProfileApplicability":"- E3 Level 1\n- E5 Level 1","SubSection":"9.1 Tenant settings","DefaultValue":"Enabled for the entire organization\nOnly allow existing codes","Level":"L1","CISControls":"[{\"version\": \"\", \"id\": \"16.10\", \"title\": \"Apply Secure Design Principles in Application\", \"description\": \"Architectures Apply secure design principles in application architectures. Secure design principles include the concept of least privilege and enforcing mediation to validate v8 every operation that the user makes, promoting the concept of \\\"never trust user - - input.\\\" Examples include ensuring that explicit error checking is performed and documented for all input, including for size, data type, and acceptable ranges or formats. Secure design also means minimizing the application infrastructure attack surface, such as turning off unprotected ports and services, removing unnecessary programs and files, and renaming or removing default accounts.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]","References":"1. https://learn.microsoft.com/en-us/power-bi/collaborate-share/service-publish-to-\nweb\n2. https://learn.microsoft.com/en-us/fabric/admin/service-admin-portal-export-\nsharing#publish-to-web","Rationale":"When using Publish to Web anyone on the Internet can view a published report or\nvisual. Viewing requires no authentication. It includes viewing detail-level data that your\nreports aggregate. By disabling the feature, restricting access to certain users and\nallowing existing embed codes organizations can mitigate the exposure of confidential\nor proprietary information.","Section":"9 Microsoft Fabric","RecommendationId":"9.1.4"}
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

    # Check the 'Publish to web' setting
    $publishToWebSetting = $tenantSettings | Where-Object { $_.settingName -eq "PublishToWeb" }

    if ($publishToWebSetting) {
        $currentState = if ($publishToWebSetting.enabled) { "Enabled" } else { "Disabled" }
        $embedCodesSetting = $publishToWebSetting.properties.embedCodesSetting
        $securityGroups = $publishToWebSetting.tenantSettingGroup

        # Determine compliance
        $isCompliant = $false
        if (-not $publishToWebSetting.enabled) {
            $isCompliant = $true
        }
        elseif ($publishToWebSetting.enabled -and $embedCodesSetting -eq "Only allow existing codes" -and $securityGroups.Count -gt 0) {
            $isCompliant = $true
        }

        # Add result to the array
        $resourceResults += @{
            ResourceName = "Publish to web"
            CurrentValue = $currentState
            IsCompliant = $isCompliant
        }
    }
    else {
        throw "Unable to retrieve 'Publish to web' setting."
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

