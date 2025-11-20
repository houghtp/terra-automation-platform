# Control: 9.1.10 - Ensure access to APIs by Service Principals is
<# CIS_METADATA_START
{"Description": "Web apps registered in Microsoft Entra ID use an assigned service principal to access\nPower BI APIs without a signed-in user. This setting allows an app to use service\nprincipal authentication.\nThe recommended state is Enabled for a subset of the organization or\nDisabled.", "Impact": "Disabled is the default behavior.", "Audit": "To audit using the UI:\n1. Navigate to Microsoft Fabric https://app.powerbi.com/admin-portal\n2. Select Tenant settings.\n3. Scroll to Developer settings.\n4. Ensure that Service principals can use Fabric APIs adheres to one of\nthese states:\no State 1: Disabled\no State 2: Enabled with Specific security groups selected and defined.\nImportant: If the organization doesn't actively use this feature it is recommended to\nkeep it Disabled.", "Remediation": "To remediate using the UI:\n1. Navigate to Microsoft Fabric https://app.powerbi.com/admin-portal\n2. Select Tenant settings.\n3. Scroll to Developer settings.\n4. Set Service principals can use Fabric APIs to one of these states:\no State 1: Disabled\no State 2: Enabled with Specific security groups selected and defined.\nImportant: If the organization doesn't actively use this feature it is recommended to\nkeep it Disabled.", "Title": "Ensure access to APIs by Service Principals is restricted", "ProfileApplicability": "- E3 Level 1\n- E5 Level 1", "SubSection": "9.1 Tenant settings", "DefaultValue": "Disabled for the entire organization", "Level": "L1", "CISControls": "[{\"version\": \"\", \"id\": \"4.8\", \"title\": \"Uninstall or Disable Unnecessary Services on\", \"description\": \"Enterprise Assets and Software Uninstall or disable unnecessary services on enterprise assets and software, - - such as an unused file sharing service, web application module, or service function.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]", "References": "1. https://learn.microsoft.com/en-us/fabric/admin/service-admin-portal-developer", "Rationale": "Leaving API access unrestricted increases the attack surface in the event an adversary\ngains access to a Service Principal. APIs are a feature-rich method for programmatic\naccess to many areas of Power Bi and should be guarded closely.", "Section": "9 Microsoft Fabric", "RecommendationId": "9.1.10"}
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
        $response = Invoke-RestMethod -Method Get -Uri $apiUrl -Headers $headers -ErrorAction Stop
    } else {
        # Fallback to Power BI session token (Service Principal - may fail with 500 error)
        Write-Warning "No user token available - using Power BI session token (may fail for Fabric Admin API)"
        $token = (Get-PowerBIAccessToken)["Authorization"]
        $headers = @{
            "Authorization" = $token
            "Content-Type" = "application/json"
        }
        $response = Invoke-RestMethod -Method Get -Uri $apiUrl -Headers $headers
    }
    
    $tenantSettings = $response.value

    # Check the setting for Service Principals using Fabric APIs
    $servicePrincipalSetting = $tenantSettings | Where-Object { $_.settingName -eq "ServicePrincipalAccessToFabricAPIs" }

    if ($servicePrincipalSetting) {
        $currentValue = if ($servicePrincipalSetting.enabled) { "Enabled" } else { "Disabled" }
        $isCompliant = (-not $servicePrincipalSetting.enabled) -or ($servicePrincipalSetting.enabled -and $servicePrincipalSetting.tenantSettingGroup -ne $null -and $servicePrincipalSetting.tenantSettingGroup.Count -gt 0)

        $resourceResults += @{
            ResourceName = "Service Principal Access to Fabric APIs"
            CurrentValue = $currentValue
            IsCompliant = $isCompliant
        }
    }
    else {
        $resourceResults += @{
            ResourceName = "Service Principal Access to Fabric APIs"
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

