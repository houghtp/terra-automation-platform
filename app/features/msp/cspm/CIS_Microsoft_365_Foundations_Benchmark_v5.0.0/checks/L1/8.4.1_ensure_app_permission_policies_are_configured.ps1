# Control: 8.4.1 - Ensure app permission policies are configured
<# CIS_METADATA_START
{"Description":"This policy setting controls which class of apps are available for users to install.","Impact":"Users will only be able to install approved classes of apps.","Audit":"To audit using the UI:\n1. Navigate to Microsoft Teams admin center\nhttps://admin.teams.microsoft.com.\n2. Click to expand Teams apps select Manage apps.\n3. In the upper right click Actions > Org-wide app settings.\n4. For Microsoft apps verify that Let users install and use available\napps by default is On or less permissive.\n5. For Third-party apps verify Let users install and use available apps\nby default is Off.\n6. For Custom apps verify Let users install and use available apps by\ndefault is Off.\n7. For Custom apps verify Let users interact with custom apps in\npreview is Off.\nNote: The Global Reader role is not able to view the Teams apps blade, Teams\nAdministrator or higher is required.","Remediation":"To remediate using the UI:\n1. Navigate to Microsoft Teams admin center\nhttps://admin.teams.microsoft.com.\n2. Click to expand Teams apps select Manage apps.\n3. In the upper right click Actions > Org-wide app settings.\n4. For Microsoft apps set Let users install and use available apps by\ndefault to On or less permissive.\n5. For Third-party apps set Let users install and use available apps\nby default to Off.\n6. For Custom apps set Let users install and use available apps by\ndefault to Off.\n7. For Custom apps set Let users interact with custom apps in preview\nto Off.","Title":"Ensure app permission policies are configured","ProfileApplicability":"- E3 Level 1\n- E5 Level 1","SubSection":"8.4 Teams apps","DefaultValue":"Microsoft apps: On\nThird-party apps: On\nCustom apps: On","Level":"L1","CISControls":"[{\"version\": \"\", \"id\": \"2.5\", \"title\": \"Allowlist Authorized Software\", \"description\": \"v8 Use technical controls, such as application allowlisting, to ensure that only - - authorized software can execute or be accessed. Reassess bi-annually, or more frequently.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"\", \"id\": \"2.7\", \"title\": \"Utilize Application Whitelisting\", \"description\": \"v7 Utilize application whitelisting technology on all assets to ensure that only - authorized software executes and all unauthorized software is blocked from executing on assets.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"\", \"id\": \"8.5\", \"title\": \"Meetings\", \"description\": \"\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]","References":"1. https://learn.microsoft.com/en-us/microsoftteams/app-centric-management\n2. https://learn.microsoft.com/en-us/defender-office-365/step-by-step-\nguides/reducing-attack-surface-in-microsoft-teams?view=o365-\nworldwide#disabling-third-party--custom-apps","Rationale":"Allowing users to install third-party or unverified apps poses a potential risk of\nintroducing malicious software to the environment.","Section":"8 Microsoft Teams admin center","RecommendationId":"8.4.1"}
CIS_METADATA_END #>
# Required Services: Teams
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()

    # Retrieve the current app permission policies
    $orgWideAppSettings = Get-CsTeamsAppPermissionPolicy -Identity "Global"

    # Check Microsoft apps setting
    $microsoftAppsCompliant = $orgWideAppSettings.AllowUserRequestsForApp -eq $true

    # Check Third-party apps setting
    $thirdPartyAppsCompliant = $orgWideAppSettings.AllowThirdPartyApps -eq $false

    # Check Custom apps setting
    $customAppsCompliant = $orgWideAppSettings.AllowCustomApps -eq $false

    # Check Custom apps preview setting
    $customAppsPreviewCompliant = $orgWideAppSettings.AllowInteractionWithCustomAppsInPreview -eq $false

    # Collect results
    $resourceResults += @{
        ResourceName = "Microsoft Apps"
        CurrentValue = $orgWideAppSettings.AllowUserRequestsForApp
        IsCompliant = $microsoftAppsCompliant
    }
    $resourceResults += @{
        ResourceName = "Third-party Apps"
        CurrentValue = $orgWideAppSettings.AllowThirdPartyApps
        IsCompliant = $thirdPartyAppsCompliant
    }
    $resourceResults += @{
        ResourceName = "Custom Apps"
        CurrentValue = $orgWideAppSettings.AllowCustomApps
        IsCompliant = $customAppsCompliant
    }
    $resourceResults += @{
        ResourceName = "Custom Apps Preview"
        CurrentValue = $orgWideAppSettings.AllowInteractionWithCustomAppsInPreview
        IsCompliant = $customAppsPreviewCompliant
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
