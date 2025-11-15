# Control: 5.2.3.6 - Ensure system-preferred multifactor authentication is
<# CIS_METADATA_START
{"RecommendationId":"5.2.3.6","Level":"L1","Title":"Ensure system-preferred multifactor authentication is enabled","Section":"5 Microsoft Entra admin center","SubSection":"5.2 Protection","ProfileApplicability":"- E3 Level 1\n- E5 Level 1","Description":"System-preferred multifactor authentication (MFA) prompts users to sign in by using the\nmost secure method they registered.\nThe user is prompted to sign-in with the most secure method according to the below\norder. The order of authentication methods is dynamic. It's updated by Microsoft as the\nsecurity landscape changes, and as better authentication methods emerge.\n1. Temporary Access Pass\n2. Passkey (FIDO2)\n3. Microsoft Authenticator notifications\n4. External authentication methods\n5. Time-based one-time password (TOTP)\n6. Telephony\n7. Certificate-based authentication\nThe recommended state is Enabled.","Rationale":"Regardless of the authentication method enabled by an administrator or set as\npreferred by the user, the system will dynamically select the most secure option\navailable at the time of authentication. This approach acts as an additional safeguard to\nprevent the use of weaker methods, such as voice calls, SMS, and email OTPs, which\nmay have been inadvertently left enabled due to misconfiguration or lack of\nconfiguration hardening.\nEnforcing the default behavior also ensures the feature is not disabled.","Impact":"The Microsoft managed value of system-preferred MFA is Enabled and as such\nenforces the default behavior. No additional impact is expected.\nNote: Due to known issues with certificate-based authentication (CBA) and system-\npreferred MFA, Microsoft moved CBA to the bottom of the list. It is still considered a\nstrong authentication method.","Audit":"To audit using the UI:\n1. Navigate to Microsoft Entra admin center https://entra.microsoft.com/.\n2. Click to expand Protection select Authentication methods.\n3. Select Settings.\n4. Verify the System-preferred multifactor authentication State is set to\nEnabled and All users are included.\n5. Ensure that only documented exclusions exist and that they are reviewed\nannually","Remediation":"To remediate using the UI:\n1. Navigate to Microsoft Entra admin center https://entra.microsoft.com/.\n2. Click to expand Protection select Authentication methods.\n3. Select Settings.\n4. Set the System-preferred multifactor authentication State to Enabled and\ninclude All users.\n5. Any users exclusions should be documented and reviewed annually.","DefaultValue":"Microsoft Managed (Enabled)","References":"1. https://learn.microsoft.com/en-us/entra/identity/authentication/concept-system-\npreferred-multifactor-authentication\n2. https://learn.microsoft.com/en-us/entra/identity/authentication/concept-system-\npreferred-multifactor-authentication#how-does-system-preferred-mfa-determine-\nthe-most-secure-method","CISControls":"[{\"version\": \"\", \"id\": \"6.3\", \"title\": \"Require MFA for Externally-Exposed Applications\", \"description\": \"v8 Require all externally-exposed enterprise or third-party applications to enforce - - MFA, where supported. Enforcing MFA through a directory service or SSO provider is a satisfactory implementation of this Safeguard. 5.2.4 Password reset\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]"}
CIS_METADATA_END #>
# Required Services: MgGraph
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()
    
    # Retrieve the authentication methods policy settings
    $authMethodsPolicy = Get-MgBetaPolicyAuthenticationMethodPolicy

    # Check if the system-preferred multifactor authentication is enabled
    $isMfaPreferredEnabled = $authMethodsPolicy.IsSystemPreferredAuthenticationMethodEnabled
    $includedUsers = $authMethodsPolicy.IncludedUsers

    # Determine compliance
    $isCompliant = $isMfaPreferredEnabled -eq $true -and $includedUsers -eq "All"

    # Add result to the results array
    $resourceResults += @{
        ResourceName = "System-Preferred MFA"
        CurrentValue = @{
            IsEnabled = $isMfaPreferredEnabled
            IncludedUsers = $includedUsers
        }
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
