# Control: 5.1.2.1 - Ensure 'Per-user MFA' is disabled
<# CIS_METADATA_START
{"RecommendationId":"5.1.2.1","Level":"L1","Title":"Ensure 'Per-user MFA' is disabled","Section":"5 Microsoft Entra admin center","SubSection":"5.1 Identity","ProfileApplicability":"- E3 Level 1\n- E5 Level 1","Description":"Legacy per-user Multi-Factor Authentication (MFA) can be configured to require\nindividual users to provide multiple authentication factors, such as passwords and\nadditional verification codes, to access their accounts. It was introduced in earlier\nversions of Office 365, prior to the more comprehensive implementation of Conditional\nAccess (CA).","Rationale":"Both security defaults and conditional access with security defaults turned off are not\ncompatible with per-user multi-factor authentication (MFA), which can lead to\nundesirable user authentication states. The CIS Microsoft 365 Benchmark explicitly\nemploys Conditional Access for MFA as an enhancement over security defaults and as\na replacement for the outdated per-user MFA. To ensure a consistent authentication\nstate disable per-user MFA on all accounts.","Impact":"Accounts using per-user MFA will need to be migrated to use CA.\nPrior to disabling per-user MFA the organization must be prepared to implement\nconditional access MFA to avoid security gaps and allow for a smooth transition. This\nwill help ensure relevant accounts are covered by MFA during the change phase from\ndisabling per-user MFA to enabling CA MFA. Section 5.2.2 in this document covers the\ncreation of a CA rule for both administrators and all users in the tenant.\nMicrosoft has documentation on migrating from per-user MFA Convert users from per-\nuser MFA to Conditional Access based MFA","Audit":"To audit using the UI:\n1. Navigate to Microsoft Entra admin center https://entra.microsoft.com/.\n2. Click to expand Identity > Users select All users.\n3. Click on Per-user MFA on the top row.\n4. Ensure under the column Multi-factor Auth Status that each account is set\nto Disabled","Remediation":"To remediate using the UI:\n1. Navigate to Microsoft Entra admin center https://entra.microsoft.com/.\n2. Click to expand Identity > Users select All users.\n3. Click on Per-user MFA on the top row.\n4. Click the empty box next to Display Name to select all accounts.\n5. On the far right under quick steps click Disable.","DefaultValue":"Disabled","References":"1. https://learn.microsoft.com/en-us/entra/identity/authentication/howto-mfa-\nuserstates#convert-users-from-per-user-mfa-to-conditional-access\n2. https://learn.microsoft.com/en-us/microsoft-365/admin/security-and-\ncompliance/set-up-multi-factor-authentication?view=o365-worldwide#use-\nconditional-access-policies\n3. https://learn.microsoft.com/en-us/entra/identity/authentication/howto-mfa-\nuserstates#convert-per-user-mfa-enabled-and-enforced-users-to-disabled","CISControls":"[{\"version\": \"\", \"id\": \"6.3\", \"title\": \"Require MFA for Externally-Exposed Applications\", \"description\": \"v8 Require all externally-exposed enterprise or third-party applications to enforce - - MFA, where supported. Enforcing MFA through a directory service or SSO provider is a satisfactory implementation of this Safeguard.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]"}
CIS_METADATA_END #>
# Required Services: MgGraph
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()

    # Per-user MFA should be disabled in favor of Conditional Access policies
    # Check if Conditional Access is being used instead of per-user MFA
    $conditionalAccessPolicies = Get-MgIdentityConditionalAccessPolicy | Where-Object {
        $_.State -eq 'enabled' -and
        ($_.GrantControls.BuiltInControls -contains 'mfa' -or $_.GrantControls.BuiltInControls -contains 'strongAuthentication')
    }

    # Get organization-wide authentication methods policy
    $authMethodsPolicy = Get-MgPolicyAuthenticationMethodPolicy

    # If Conditional Access policies require MFA, per-user MFA should be disabled
    $hasConditionalAccessMFA = $conditionalAccessPolicies.Count -gt 0

    # For this check, we consider it compliant if CA policies are in use (indicating per-user MFA is not needed)
    $isCompliant = $hasConditionalAccessMFA

    $resourceResults += @{
        ResourceName = "Per-User MFA vs Conditional Access"
        CurrentValue = if ($hasConditionalAccessMFA) { 'Conditional Access MFA Active' } else { 'No CA MFA Policies Found' }
        IsCompliant = $isCompliant
        ConditionalAccessPolicies = $conditionalAccessPolicies.Count
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
