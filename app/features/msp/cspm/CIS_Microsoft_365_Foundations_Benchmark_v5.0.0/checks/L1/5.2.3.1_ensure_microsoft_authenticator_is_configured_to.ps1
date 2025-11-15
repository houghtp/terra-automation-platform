# Control: 5.2.3.1 - Ensure Microsoft Authenticator is configured to
<# CIS_METADATA_START
{"RecommendationId":"5.2.3.1","Level":"L1","Title":"Ensure Microsoft Authenticator is configured to protect against MFA fatigue","Section":"5 Microsoft Entra admin center","SubSection":"5.2 Protection","ProfileApplicability":"- E3 Level 1\n- E5 Level 1","Description":"Microsoft provides supporting settings to enhance the configuration of the Microsoft\nAuthenticator application. These settings provide users with additional information and\ncontext when they receive MFA passwordless and push requests, including the\ngeographic location of the request, the requesting application, and a requirement for\nnumber matching.\nEnsure the following are Enabled.\n- Require number matching for push notifications\n- Show application name in push and passwordless notifications\n- Show geographic location in push and passwordless notifications\nNOTE: On February 27, 2023 Microsoft started enforcing number matching tenant-wide\nfor all users using Microsoft Authenticator.","Rationale":"As the use of strong authentication has become more widespread, attackers have\nstarted to exploit the tendency of users to experience \"MFA fatigue.\" This occurs when\nusers are repeatedly asked to provide additional forms of identification, leading them to\neventually approve requests without fully verifying the source. To counteract this,\nnumber matching can be employed to ensure the security of the authentication process.\nWith this method, users are prompted to confirm a number displayed on their original\ndevice and enter it into the device being used for MFA. Additionally, other information\nsuch as geolocation and application details are displayed to enhance the end user's\nawareness. Among these 3 options, number matching provides the strongest net\nsecurity gain.","Impact":"Additional interaction will be required by end users using number matching as opposed\nto simply pressing \"Approve\" for login attempts.","Audit":"To audit using the UI:\n1. Navigate to the Microsoft Entra admin center https://entra.microsoft.com.\n2. Click to expand Protection > Authentication methods select Policies.\n3. Under Method select Microsoft Authenticator.\n4. Under Enable and Target verify the setting is set to Enable.\n5. In the Include tab ensure All users is selected.\n6. In the Exclude tab ensure only valid groups are present (i.e. Break Glass\naccounts).\n7. Select Configure\n8. Verify the following Microsoft Authenticator settings:\no Require number matching for push notifications Status is set to\nEnabled, Target All users\no Show application name in push and passwordless notifications\nis set to Enabled, Target All users\no Show geographic location in push and passwordless\nnotifications is set to Enabled, Target All users\n9. In each setting select Exclude and verify only groups are present (i.e. Break\nGlass accounts).","Remediation":"To remediate using the UI:\n1. Navigate to the Microsoft Entra admin center https://entra.microsoft.com.\n2. Click to expand Protection > Authentication methods select Policies.\n3. Select Microsoft Authenticator\n4. Under Enable and Target ensure the setting is set to Enable.\n5. Select Configure\n6. Set the following Microsoft Authenticator settings:\no Require number matching for push notifications Status is set to\nEnabled, Target All users\no Show application name in push and passwordless notifications\nis set to Enabled, Target All users\no Show geographic location in push and passwordless\nnotifications is set to Enabled, Target All users\nNote: Valid groups such as break glass accounts can be excluded per organization\npolicy.","DefaultValue":"Microsoft-managed","References":"1. https://learn.microsoft.com/en-us/entra/identity/authentication/concept-\nauthentication-default-enablement\n2. https://techcommunity.microsoft.com/t5/microsoft-entra-blog/defend-your-users-\nfrom-mfa-fatigue-attacks/ba-p/2365677\n3. https://learn.microsoft.com/en-us/entra/identity/authentication/how-to-mfa-\nnumber-match","CISControls":"[{\"version\": \"\", \"id\": \"6.4\", \"title\": \"Require MFA for Remote Network Access\", \"description\": \"v8 - - - Require MFA for remote network access.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]"}
CIS_METADATA_END #>
# Required Services: MgGraph
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()
    
    # Retrieve Microsoft Authenticator policy settings
    $authenticatorPolicy = Get-MgBetaPolicyAuthenticationMethodPolicy

    # Check if Microsoft Authenticator is enabled
    $isEnabled = $authenticatorPolicy.State -eq "enabled"
    
    # Check if number matching is required
    $numberMatchingEnabled = $authenticatorPolicy.Settings.NumberMatchingRequired -eq $true
    
    # Check if application name is shown in notifications
    $appNameShown = $authenticatorPolicy.Settings.ShowApplicationName -eq $true
    
    # Check if geographic location is shown in notifications
    $geoLocationShown = $authenticatorPolicy.Settings.ShowGeographicLocation -eq $true
    
    # Compile results
    $resourceResults += @{
        Setting = "Microsoft Authenticator Enabled"
        CurrentValue = $authenticatorPolicy.State
        IsCompliant = $isEnabled
    }
    $resourceResults += @{
        Setting = "Require Number Matching"
        CurrentValue = $authenticatorPolicy.Settings.NumberMatchingRequired
        IsCompliant = $numberMatchingEnabled
    }
    $resourceResults += @{
        Setting = "Show Application Name"
        CurrentValue = $authenticatorPolicy.Settings.ShowApplicationName
        IsCompliant = $appNameShown
    }
    $resourceResults += @{
        Setting = "Show Geographic Location"
        CurrentValue = $authenticatorPolicy.Settings.ShowGeographicLocation
        IsCompliant = $geoLocationShown
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
