# Control: 9.1.6 - Ensure 'Allow users to apply sensitivity labels for
<# CIS_METADATA_START
{"Description": "Information protection tenant settings help to protect sensitive information in the Power\nBI tenant. Allowing and applying sensitivity labels to content ensures that information is\nonly seen and accessed by the appropriate users.\nThe recommended state is Enabled or Enabled for a subset of the\norganization.\nNote: Sensitivity labels and protection are only applied to files exported to Excel,\nPowerPoint, or PDF files, that are controlled by \"Export to Excel\" and \"Export reports as\nPowerPoint presentation or PDF documents\" settings. All other export and sharing\noptions do not support the application of sensitivity labels and protection.\nNote 2: There are some prerequisite steps that need to be completed in order to fully\nutilize labeling. See here.", "Impact": "Additional license requirements like Power BI Pro are required, as outlined in the\nLicensed and requirements page linked in the description and references sections.", "Audit": "To audit using the UI:\n1. Navigate to Microsoft Fabric https://app.powerbi.com/admin-portal\n2. Select Tenant settings.\n3. Scroll to Information protection.\n4. Ensure that Allow users to apply sensitivity labels for content\nadheres to one of these states:\no State 1: Enabled\no State 2: Enabled with Specific security groups selected and defined.", "Remediation": "To remediate using the UI:\n1. Navigate to Microsoft Fabric https://app.powerbi.com/admin-portal\n2. Select Tenant settings.\n3. Scroll to Information protection.\n4. Set Allow users to apply sensitivity labels for content to one of\nthese states:\no State 1: Enabled\no State 2: Enabled with Specific security groups selected and defined.", "Title": "Ensure 'Allow users to apply sensitivity labels for content' is 'Enabled'", "ProfileApplicability": "- E3 Level 1\n- E5 Level 1", "SubSection": "9.1 Tenant settings", "DefaultValue": "Disabled", "Level": "L1", "CISControls": "[{\"version\": \"\", \"id\": \"3.2\", \"title\": \"Establish and Maintain a Data Inventory\", \"description\": \"v8 Establish and maintain a data inventory, based on the enterprise's data - - - management process. Inventory sensitive data, at a minimum. Review and update inventory annually, at a minimum, with a priority on sensitive data.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"\", \"id\": \"3.7\", \"title\": \"Establish and Maintain a Data Classification Scheme\", \"description\": \"Establish and maintain an overall data classification scheme for the enterprise. v8 Enterprises may use labels, such as \\\"Sensitive,\\\" \\\"Confidential,\\\" and \\\"Public,\\\" and - - classify their data according to those labels. Review and update the classification scheme annually, or when significant enterprise changes occur that could impact this Safeguard.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]", "References": "1. https://learn.microsoft.com/en-us/power-bi/enterprise/service-security-enable-\ndata-sensitivity-labels\n2. https://learn.microsoft.com/en-us/fabric/governance/data-loss-prevention-\noverview\n3. https://learn.microsoft.com/en-us/power-bi/enterprise/service-security-enable-\ndata-sensitivity-labels#licensing-and-requirements", "Rationale": "Establishing data classifications and affixing labels to data at creation enables\norganizations to discern the data's criticality, sensitivity, and value. This initial\nidentification enables the implementation of appropriate protective measures, utilizing\ntechnologies like Data Loss Prevention (DLP) to avert inadvertent exposure and\nenforcing access controls to safeguard against unauthorized access.\nThis practice can also promote user awareness and responsibility in regard to the\nnature of the data they interact with. Which in turn can foster awareness in other areas\nof data management across the organization.", "Section": "9 Microsoft Fabric", "RecommendationId": "9.1.6"}
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

    # Check the specific setting for sensitivity labels
    $sensitivityLabelSetting = $tenantSettings | Where-Object { $_.DisplayName -eq "Allow users to apply sensitivity labels for content" }

    if ($null -ne $sensitivityLabelSetting) {
        $currentValue = if ($1.enabled) { "Enabled" } else { "Disabled" }
        $isCompliant = $blockResourceKeyAuthSetting.enabled -or $currentValue -eq "Enabled with Specific security groups selected and defined"

        $resourceResults += @{
            ResourceName = "Power BI Sensitivity Label Setting"
            CurrentValue = $currentValue
            IsCompliant = $isCompliant
        }
    }
    else {
        $resourceResults += @{
            ResourceName = "Power BI Sensitivity Label Setting"
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

