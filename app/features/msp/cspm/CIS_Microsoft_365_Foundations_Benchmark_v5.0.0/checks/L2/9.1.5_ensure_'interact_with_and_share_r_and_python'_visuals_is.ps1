# Control: 9.1.5 - Ensure 'Interact with and share R and Python' visuals is
<# CIS_METADATA_START
{"Description": "Power BI allows the integration of R and Python scripts directly into visuals. This feature\nallows data visualizations by incorporating custom calculations, statistical analyses,\nmachine learning models, and more using R or Python scripts. Custom visuals can be\ncreated by embedding them directly into Power BI reports. Users can then interact with\nthese visuals and see the results of the custom code within the Power BI interface.", "Impact": "Use of R and Python scripting will require exceptions for developers, along with more\nstringent code review.", "Audit": "To audit using the UI:\n1. Navigate to Microsoft Fabric https://app.powerbi.com/admin-portal\n2. Select Tenant settings.\n3. Scroll to R and Python visuals settings.\n4. Ensure that Interact with and share R and Python visuals is Disabled", "Remediation": "To remediate using the UI:\n1. Navigate to Microsoft Fabric https://app.powerbi.com/admin-portal\n2. Select Tenant settings.\n3. Scroll to R and Python visuals settings.\n4. Set Interact with and share R and Python visuals to Disabled", "Title": "Ensure 'Interact with and share R and Python' visuals is 'Disabled'", "ProfileApplicability": "- E3 Level 2\n- E5 Level 2", "SubSection": "9.1 Tenant settings", "DefaultValue": "Enabled", "Level": "L2", "CISControls": "[{\"version\": \"\", \"id\": \"4.8\", \"title\": \"Uninstall or Disable Unnecessary Services on\", \"description\": \"Enterprise Assets and Software Uninstall or disable unnecessary services on enterprise assets and software, - - such as an unused file sharing service, web application module, or service function.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]", "References": "1. https://learn.microsoft.com/en-us/fabric/admin/service-admin-portal-r-python-\nvisuals\n2. https://learn.microsoft.com/en-us/power-bi/visuals/service-r-visuals\n3. https://www.r-project.org/", "Rationale": "Disabling this feature can reduce the attack surface by preventing potential malicious\ncode execution leading to data breaches, or unauthorized access. The potential for\nsensitive or confidential data being leaked to unintended users is also increased with\nthe use of scripts.", "Section": "9 Microsoft Fabric", "RecommendationId": "9.1.5"}
CIS_METADATA_END #>
# Required Services: Power BI (with user token for Fabric Admin API)
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()

    # Retrieve Power BI tenant settings using user token (hybrid authentication)
    # Check if user token is available (set by Connect-M365.ps1)
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

    # Check the setting for 'Interact with and share R and Python visuals'
    $rPythonVisualsSetting = $tenantSettings | Where-Object { $_.settingName -eq "RAndPythonVisualsEnabled" }

    if ($rPythonVisualsSetting) {
        $currentValue = if ($1.enabled) { "Enabled" } else { "Disabled" }
        $isCompliant = $currentValue -eq $false

        $resourceResults += @{
            ResourceName = "R and Python Visuals Setting"
            CurrentValue = $currentValue
            IsCompliant = $isCompliant
        }
    }
    else {
        throw "R and Python visuals setting not found."
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

