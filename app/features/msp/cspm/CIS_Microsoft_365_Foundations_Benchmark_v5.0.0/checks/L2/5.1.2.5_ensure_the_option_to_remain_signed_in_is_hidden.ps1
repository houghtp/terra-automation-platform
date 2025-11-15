# Control: 5.1.2.5 - Ensure the option to remain signed in is hidden
<# CIS_METADATA_START
{"RecommendationId":"5.1.2.5","Level":"L2","Title":"Ensure the option to remain signed in is hidden","Section":"5 Microsoft Entra admin center","SubSection":"5.1 Identity","ProfileApplicability":"- E3 Level 2\n- E5 Level 2","Description":"The option for the user to Stay signed in, or the Keep me signed in option, will\nprompt a user after a successful login. When the user selects this option, a persistent\nrefresh token is created. The refresh token lasts for 90 days by default and does not\nprompt for sign-in or multifactor.","Rationale":"Allowing users to select this option presents risk, especially if the user signs into their\naccount on a publicly accessible computer/web browser. In this case it would be trivial\nfor an unauthorized person to gain access to any associated cloud data from that\naccount.","Impact":"Once this setting is hidden users will no longer be prompted upon sign-in with the\nmessage Stay signed in?. This may mean users will be forced to sign in more\nfrequently. Important: some features of SharePoint Online and Office 2010 have a\ndependency on users remaining signed in. If you hide this option, users may get\nadditional and unexpected sign in prompts.","Audit":"To audit using the UI:\n1. Navigate to Microsoft Entra admin center https://entra.microsoft.com/.\n2. Click to expand Identity> Users > User settings.\n3. Ensure Show keep user signed in is highlighted No.","Remediation":"To remediate using the UI:\n1. Navigate to Microsoft Entra admin center https://entra.microsoft.com/.\n2. Click to expand Identity> Users > User settings.\n3. Set Show keep user signed in to No.\n4. Click Save.","DefaultValue":"Users may select stay signed in","References":"1. https://learn.microsoft.com/en-us/entra/identity/authentication/concepts-azure-\nmulti-factor-authentication-prompts-session-lifetime\n2. https://learn.microsoft.com/en-us/entra/fundamentals/how-to-manage-stay-\nsigned-in-prompt","CISControls":"[{\"version\": \"\", \"id\": \"16.3\", \"title\": \"Require Multi-factor Authentication\", \"description\": \"Require multi-factor authentication for all user accounts, on all systems, - - whether managed onsite or by a third-party provider.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]"}
CIS_METADATA_END #>
# Required Services: MgGraph
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()
    
    # Retrieve the tenant-wide settings for user sign-in
    $settings = Get-MgBetaOrganizations
    
    # Check if the "Show keep user signed in" option is set to No
    $currentValue = $settings.UserSettings.ShowKeepUserSignedIn
    $isCompliant = $currentValue -eq $false
    
    # Add the result to the results array
    $resourceResults += @{
        ResourceName = "Tenant User Settings"
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
