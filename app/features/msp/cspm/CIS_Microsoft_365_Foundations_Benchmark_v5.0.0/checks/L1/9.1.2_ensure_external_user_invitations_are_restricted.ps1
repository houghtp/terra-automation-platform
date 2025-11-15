# Control: 9.1.2 - Ensure external user invitations are restricted
<# CIS_METADATA_START
{"Description":"This setting helps organizations choose whether new external users can be invited to\nthe organization through Power BI sharing, permissions, and subscription experiences.\nThis setting only controls the ability to invite through Power BI.\nThe recommended state is Enabled for a subset of the organization or\nDisabled.\nNote: To invite external users to the organization, the user must also have the Microsoft\nEntra Guest Inviter role.","Impact":"Guest user invitations will be limited to only specific employees.","Audit":"To audit using the UI:\n1. Navigate to Microsoft Fabric https://app.powerbi.com/admin-portal\n2. Select Tenant settings.\n3. Scroll to Export and Sharing settings.\n4. Ensure that Users can invite guest users to collaborate through\nitem sharing and permissions adheres to one of these states:\no State 1: Disabled\no State 2: Enabled with Specific security groups selected and defined.\nImportant: If the organization doesn't actively use this feature it is recommended to\nkeep it Disabled.","Remediation":"To remediate using the UI:\n1. Navigate to Microsoft Fabric https://app.powerbi.com/admin-portal\n2. Select Tenant settings.\n3. Scroll to Export and Sharing settings.\n4. Set Users can invite guest users to collaborate through item\nsharing and permissions to one of these states:\no State 1: Disabled\no State 2: Enabled with Specific security groups selected and defined.\nImportant: If the organization doesn't actively use this feature it is recommended to\nkeep it Disabled.","Title":"Ensure external user invitations are restricted","ProfileApplicability":"- E3 Level 1\n- E5 Level 1","SubSection":"9.1 Tenant settings","DefaultValue":"Enabled for the entire organization","Level":"L1","CISControls":"[{\"version\": \"\", \"id\": \"6.8\", \"title\": \"Define and Maintain Role-Based Access Control\", \"description\": \"Define and maintain role-based access control, through determining and v8 documenting the access rights necessary for each role within the enterprise to - successfully carry out its assigned duties. Perform access control reviews of enterprise assets to validate that all privileges are authorized, on a recurring schedule at a minimum annually, or more frequently.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]","References":"1. https://learn.microsoft.com/en-us/fabric/admin/service-admin-portal-export-\nsharing\n2. https://learn.microsoft.com/en-us/power-bi/enterprise/service-admin-azure-ad-\nb2b#invite-guest-users","Rationale":"Establishing and enforcing a dedicated security group prevents unauthorized access to\nMicrosoft Fabric for guests collaborating in Azure that are new or assigned guest status\nfrom other applications. This upholds the principle of least privilege and uses role-based\naccess control (RBAC). These security groups can also be used for tasks like\nconditional access, enhancing risk management and user accountability across the\norganization.","Section":"9 Microsoft Fabric","RecommendationId":"9.1.2"}
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

    # Check the specific setting for external user invitations
    $externalUserInvitationSetting = $tenantSettings | Where-Object { $_.settingName -eq "Users can invite guest users to collaborate through item sharing and permissions" }

    # Determine compliance based on the setting value
    $isCompliant = $false
    if ($externalUserInvitationSetting) {
        if (-not $externalUserInvitationSetting.enabled -or ($externalUserInvitationSetting.enabled -and $externalUserInvitationSetting.tenantSettingGroup -ne $null)) {
            $isCompliant = $true
        }

        $resourceResults += @{
            ResourceName = "Power BI Tenant Setting"
            CurrentValue = $externalUserInvitationSetting.State
            IsCompliant = $isCompliant
        }
    }
    else {
        $resourceResults += @{
            ResourceName = "Power BI Tenant Setting"
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

