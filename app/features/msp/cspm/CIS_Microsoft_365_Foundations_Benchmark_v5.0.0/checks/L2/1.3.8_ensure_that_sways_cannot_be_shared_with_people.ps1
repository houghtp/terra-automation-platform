# Control: 1.3.8 - Ensure that Sways cannot be shared with people
<# CIS_METADATA_START
{"Description":"Sway is a Microsoft 365 app that lets organizations create interactive, web-based\npresentations using images, text, videos and other media. Its design engine simplifies\nthe process, allowing for quick customization. Presentations can then be shared via a\nlink.\nThis setting controls user Sway sharing capability, both within and outside of the\norganization. By default, Sway is enabled for everyone in the organization.","Impact":"Interactive reports, presentations, newsletters, and other items created in Sway will not\nbe shared outside the organization by users.","Audit":"To audit using the UI:\n1. Navigate to Microsoft 365 admin center https://admin.microsoft.com.\n2. Click to expand Settings then select Org settings.\n3. Under Services select Sway.\n4. Confirm that under Sharing the following is not checked\no Option: Let people in your organization share their sways\nwith people outside your organization.","Remediation":"To remediate using the UI:\n1. Navigate to Microsoft 365 admin center https://admin.microsoft.com.\n2. Click to expand Settings then select Org settings.\n3. Under Services select Sway\no Uncheck: Let people in your organization share their sways\nwith people outside your organization.\n4. Click Save.","Title":"Ensure that Sways cannot be shared with people","ProfileApplicability":"- E3 Level 2\n- E5 Level 2","SubSection":"1.3 Settings","DefaultValue":"Let people in your organization share their sways with people outside\nyour organization - Enabled","Level":"L2","CISControls":"[{\"version\": \"\", \"id\": \"4.8\", \"title\": \"Uninstall or Disable Unnecessary Services on\", \"description\": \"Enterprise Assets and Software Uninstall or disable unnecessary services on enterprise assets and software, - - such as an unused file sharing service, web application module, or service function.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"v8\", \"id\": \"13.1\", \"title\": \"Maintain an Inventory Sensitive Information\", \"description\": \"v7 Maintain an inventory of all sensitive information stored, processed, or - - - transmitted by the organization's technology systems, including those located onsite or at a remote service provider. 2 Microsoft 365 Defender Microsoft 365 Defender, also known as Security, contains settings relating to policies, rules, and security controls that are common to many Microsoft 365 applications. Direct link: https://security.microsoft.com/\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"v8\", \"id\": \"2.1\", \"title\": \"Email & collaboration\", \"description\": \"\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]","References":"1. https://support.microsoft.com/en-us/office/administrator-settings-for-sway-\nd298e79b-b6ab-44c6-9239-aa312f5784d4\n2. https://learn.microsoft.com/en-us/office365/servicedescriptions/microsoft-sway-\nservice-description","Rationale":"Disable external sharing of Sway documents that can contain sensitive information to\nprevent accidental or arbitrary data leaks.","Section":"1 Microsoft 365 admin center","RecommendationId":"1.3.8"}
CIS_METADATA_END #>
# Required Services: MgGraph
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()
    
    # Retrieve the Sway settings for the organization
    $swaySettings = Get-MgBetaOrganizationsSway

    # Check if the setting to allow sharing Sways with people outside the organization is disabled
    $isCompliant = -not $swaySettings.AllowExternalSharing

    # Add the result to the results array
    $resourceResults += @{
        ResourceName = "Sway External Sharing"
        CurrentValue = $swaySettings.AllowExternalSharing
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
