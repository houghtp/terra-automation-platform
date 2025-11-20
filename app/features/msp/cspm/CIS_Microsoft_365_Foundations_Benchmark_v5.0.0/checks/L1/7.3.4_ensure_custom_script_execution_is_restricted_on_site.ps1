# Control: 7.3.4 - Ensure custom script execution is restricted on site
<# CIS_METADATA_START
{"Description": "This setting controls custom script execution on a particular site (previously called \"site\ncollection\").\nCustom scripts can allow users to change the look, feel and behavior of sites and\npages. Every script that runs in a SharePoint page (whether it's an HTML page in a\ndocument library or a JavaScript in a Script Editor Web Part) always runs in the context\nof the user visiting the page and the SharePoint application. This means:\n- Scripts have access to everything the user has access to.\n- Scripts can access content across several Microsoft 365 services and even\nbeyond with Microsoft Graph integration.\nThe recommended state is DenyAddAndCustomizePages set to $true.", "Impact": "None - this is the default behavior.", "Audit": "To audit using PowerShell:\n1. Connect to SharePoint Online using Connect-SPOService.\n2. Run the following PowerShell command to show non-compliant results:\nGet-SPOSite | Where-Object { $_.DenyAddAndCustomizePages -eq \"Disabled\" `\n-and $_.Url -notlike \"*-my.sharepoint.com/\" } |\nft Title, Url, DenyAddAndCustomizePages\n3. Ensure the returned value is for DenyAddAndCustomizePages is Enabled for\neach site.\nNote: The property DenyAddAndCustomizePages cannot be set on the MySite host,\nwhich is displayed with a URL like https://tenant id-my.sharepoint.com/", "Remediation": "To remediate using PowerShell:\n1. Connect to SharePoint Online using Connect-SPOService.\n2. Edit the below and run for each site as needed:\nSet-SPOSite -Identity <SiteUrl> -DenyAddAndCustomizePages $true\nNote: The property DenyAddAndCustomizePages cannot be set on the MySite host,\nwhich is displayed with a URL like https://tenant id-my.sharepoint.com/", "Title": "Ensure custom script execution is restricted on site collections", "ProfileApplicability": "- E3 Level 1\n- E5 Level 1", "SubSection": "7.3 Settings", "DefaultValue": "DenyAddAndCustomizePages $true or Enabled", "Level": "L1", "CISControls": "[{\"version\": \"\", \"id\": \"2.7\", \"title\": \"Allowlist Authorized Scripts\", \"description\": \"Use technical controls, such as digital signatures and version control, to ensure that only authorized scripts, such as specific .ps1, .py, etc., files, are allowed to - execute. Block unauthorized scripts from executing. Reassess bi-annually, or more frequently. 8 Microsoft Teams admin center The Microsoft Teams admin center contains settings related to Microsoft Teams. UI Direct link: https://admin.teams.microsoft.com/ The PowerShell module most commonly used in this section is MicrosoftTeams and uses Connect-MicrosoftTeams as the connection cmdlet. The latest version of the module can be downloaded here: https://www.powershellgallery.com/packages/MicrosoftTeams/\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"v8\", \"id\": \"8.1\", \"title\": \"Teams\", \"description\": \"\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]", "References": "1. https://learn.microsoft.com/en-us/sharepoint/allow-or-prevent-custom-script\n2. https://learn.microsoft.com/en-us/sharepoint/security-considerations-of-allowing-\ncustom-script\n3. https://learn.microsoft.com/en-us/powershell/module/sharepoint-online/set-\nsposite?view=sharepoint-ps", "Rationale": "Custom scripts could contain malicious instructions unknown to the user or\nadministrator. When users are allowed to run custom script, the organization can no\nlonger enforce governance, scope the capabilities of inserted code, block specific parts\nof code, or block all custom code that has been deployed. If scripting is allowed the\nfollowing things can't be audited:\n- What code has been inserted\n- Where the code has been inserted\n- Who inserted the code\nNote: Microsoft recommends using the SharePoint Framework instead of custom\nscripts.", "Section": "7 SharePoint admin center", "RecommendationId": "7.3.4"}
CIS_METADATA_END #>
# Required Services: SharePoint
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()

    # Adapted script logic from the original script
    # Get all SharePoint Online sites and check for DenyAddAndCustomizePages setting
    $sites = Get-PnPTenantSite | Where-Object { $_.DenyAddAndCustomizePages -eq "Disabled" -and $_.Url -notlike "*-my.sharepoint.com/" }

    foreach ($site in $sites) {
        $resourceResults += @{
            Title = $site.Title
            Url = $site.Url
            DenyAddAndCustomizePages = $site.DenyAddAndCustomizePages
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
