# Control: 7.3.3 - Ensure custom script execution is restricted on
<# CIS_METADATA_START
{"Description":"This setting controls custom script execution on self-service created sites.\nCustom scripts can allow users to change the look, feel and behavior of sites and\npages. Every script that runs in a SharePoint page (whether it's an HTML page in a\ndocument library or a JavaScript in a Script Editor Web Part) always runs in the context\nof the user visiting the page and the SharePoint application. This means:\n- Scripts have access to everything the user has access to.\n- Scripts can access content across several Microsoft 365 services and even\nbeyond with Microsoft Graph integration.\nThe recommended state is Prevent users from running custom script on\nself-service created sites.","Impact":"None - this is the default behavior.","Audit":"To audit using the UI:\n1. Navigate to SharePoint admin center https://admin.microsoft.com/sharepoint\n2. Select Settings.\n3. At the bottom of the page click the classic settings page hyperlink.\n4. Scroll to locate the Custom Script section. On the right ensure the following:\no Verify Prevent users from running custom script on self-\nservice created sites is set.\nNote: The classic settings page link will not appear for Global Readers. Accessing this\npage requires being a member of the role SharePoint Administrator.","Remediation":"To remediate using the UI:\n1. Navigate to SharePoint admin center https://admin.microsoft.com/sharepoint\n2. Select Settings.\n3. At the bottom of the page click the classic settings page hyperlink.\n4. Scroll to locate the Custom Script section. On the right set the following:\no Select Prevent users from running custom script on self-\nservice created sites.","Title":"Ensure custom script execution is restricted on","ProfileApplicability":"- E3 Level 1\n- E5 Level 1","SubSection":"7.3 Settings","DefaultValue":"Selected Prevent users from running custom script on self-service\ncreated sites","Level":"L1","CISControls":"[{\"version\": \"\", \"id\": \"2.7\", \"title\": \"Allowlist Authorized Scripts\", \"description\": \"Use technical controls, such as digital signatures and version control, to ensure that only authorized scripts, such as specific .ps1, .py, etc., files, are allowed to - execute. Block unauthorized scripts from executing. Reassess bi-annually, or more frequently.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]","References":"1. https://learn.microsoft.com/en-us/sharepoint/allow-or-prevent-custom-script\n2. https://learn.microsoft.com/en-us/sharepoint/security-considerations-of-allowing-\ncustom-script\n3. https://learn.microsoft.com/en-us/powershell/module/sharepoint-online/set-\nsposite?view=sharepoint-ps","Rationale":"Custom scripts could contain malicious instructions unknown to the user or\nadministrator. When users are allowed to run custom script, the organization can no\nlonger enforce governance, scope the capabilities of inserted code, block specific parts\nof code, or block all custom code that has been deployed. If scripting is allowed the\nfollowing things can't be audited:\n- What code has been inserted\n- Where the code has been inserted\n- Who inserted the code\nNote: Microsoft recommends using the SharePoint Framework instead of custom\nscripts.","Section":"7 SharePoint admin center","RecommendationId":"7.3.3"}
CIS_METADATA_END #>
# Required Services: SharePoint
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()

    # Retrieve SharePoint tenant settings for custom script on self-service created sites
    $tenant = Get-PnPTenant

    # Check if custom script is disabled on self-service created sites
    # DenyAddAndCustomizePagesStatus: 1 = Enabled (custom script denied/disabled), 2 = Disabled (custom script allowed)
    $isCustomScriptDisabled = $tenant.DenyAddAndCustomizePagesStatus -eq 1

    # Add result to the results array
    $resourceResults += @{
        ResourceName = "Self-Service Created Sites"
        CurrentValue = if ($tenant.DenyAddAndCustomizePagesStatus -eq 1) { "Disabled (Compliant)" } else { "Enabled (Non-Compliant)" }
        IsCompliant = $isCustomScriptDisabled
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
