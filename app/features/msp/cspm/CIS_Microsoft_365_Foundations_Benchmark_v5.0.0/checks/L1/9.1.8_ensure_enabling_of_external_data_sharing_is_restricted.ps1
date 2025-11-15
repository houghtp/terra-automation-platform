# Control: 9.1.8 - Ensure enabling of external data sharing is restricted
<# CIS_METADATA_START
{"Description":"Power BI admins can specify which users or user groups can share datasets externally\nwith guests from a different tenant through the in-place mechanism. Disabling this\nsetting prevents any user from sharing datasets externally by restricting the ability of\nusers to turn on external sharing for datasets they own or manage.\nThe recommended state is Enabled for a subset of the organization or\nDisabled.","Impact":"Security groups will need to be more closely tended to and monitored.","Audit":"To audit using the UI:\n1. Navigate to Microsoft Fabric https://app.powerbi.com/admin-portal\n2. Select Tenant settings.\n3. Scroll to Export and Sharing settings.\n4. Ensure that Allow specific users to turn on external data sharing\nadheres to one of these states:\no State 1: Disabled\no State 2: Enabled with Specific security groups selected and defined.\nImportant: If the organization doesn't actively use this feature it is recommended to\nkeep it Disabled.","Remediation":"To remediate using the UI:\n1. Navigate to Microsoft Fabric https://app.powerbi.com/admin-portal\n2. Select Tenant settings.\n3. Scroll to Export and Sharing settings.\n4. Set Allow specific users to turn on external data sharing to one of\nthese states:\no State 1: Disabled\no State 2: Enabled with Specific security groups selected and defined.\nImportant: If the organization doesn't actively use this feature it is recommended to\nkeep it Disabled.","Title":"Ensure enabling of external data sharing is restricted","ProfileApplicability":"- E3 Level 1\n- E5 Level 1","SubSection":"9.1 Tenant settings","DefaultValue":"Enabled for the entire organization","Level":"L1","CISControls":"[{\"version\": \"\", \"id\": \"3.3\", \"title\": \"Configure Data Access Control Lists\", \"description\": \"v8 Configure data access control lists based on a user's need to know. Apply data - - - access control lists, also known as access permissions, to local and remote file systems, databases, and applications.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"\", \"id\": \"6.8\", \"title\": \"Define and Maintain Role-Based Access Control\", \"description\": \"Define and maintain role-based access control, through determining and v8 documenting the access rights necessary for each role within the enterprise to - successfully carry out its assigned duties. Perform access control reviews of enterprise assets to validate that all privileges are authorized, on a recurring schedule at a minimum annually, or more frequently.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]","References":"1. https://learn.microsoft.com/en-us/fabric/admin/service-admin-portal-export-\nsharing","Rationale":"Establishing and enforcing a dedicated security group prevents unauthorized access to\nMicrosoft Fabric for guests collaborating in Azure that are new or from other\napplications. This upholds the principle of least privilege and uses role-based access\ncontrol (RBAC). These security groups can also be used for tasks like conditional\naccess, enhancing risk management and user accountability across the organization.","Section":"9 Microsoft Fabric","RecommendationId":"9.1.8"}
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

    # Check the specific setting for external data sharing
    $externalDataSharingSetting = $tenantSettings | Where-Object { $_.settingName -eq "EnableDatasetInPlaceSharing" }

    if ($null -eq $externalDataSharingSetting) {
        throw "External data sharing setting not found."
    }

    # Determine compliance based on the setting value
    $currentValue = if ($externalDataSharingSetting.enabled) { "Enabled" } else { "Disabled" }
    $isCompliant = $currentValue -eq "Disabled" -or ($currentValue -eq "Enabled" -and $null -ne $externalDataSharingSetting.SecurityGroups -and $externalDataSharingSetting.SecurityGroups.Count -gt 0)

    # Add result to the results array
    $resourceResults += @{
        ResourceName = "External Data Sharing"
        CurrentValue = $currentValue
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

