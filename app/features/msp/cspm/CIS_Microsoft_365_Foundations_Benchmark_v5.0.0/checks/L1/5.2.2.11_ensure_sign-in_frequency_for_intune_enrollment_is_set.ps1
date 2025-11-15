# Control: 5.2.2.11 - Ensure sign-in frequency for Intune Enrollment is set
<# CIS_METADATA_START
{"RecommendationId":"5.2.2.11","Level":"L1","Title":"Ensure sign-in frequency for Intune Enrollment is set to 'Every time'","Section":"5 Microsoft Entra admin center","SubSection":"5.2 Protection","ProfileApplicability":"- E3 Level 1\n- E5 Level 1","Description":"Sign-in frequency defines the time period before a user is asked to sign in again when\nattempting to access a resource. The Microsoft Entra ID default configuration for user\nsign-in frequency is a rolling window of 90 days.\nThe recommended state is a Sign-in frequency of Every time for Microsoft\nIntune Enrollment\nNote: Microsoft accounts for a five-minute clock skew when 'every time' is selected in a\nconditional access policy, ensuring that users are not prompted more frequently than\nonce every five minutes.","Rationale":"Intune Enrollment is considered a sensitive action and should be safeguarded. An\nattack path exists that allows for a bypass of device compliance Conditional Access\nrule. This could allow compromised credentials to be used through a newly registered\ndevice enrolled in Intune, enabling persistence and privilege escalation.\nSetting sign-in frequency to every time limits the timespan an attacker could use fresh\ncredentials to enroll a new device to Intune.","Impact":"New users enrolling into Intune through an automated process may need to sign-in\nagain if the enrollment process goes on for too long.","Audit":"To audit using the UI:\n1. Navigate to the Microsoft Entra admin center https://entra.microsoft.com.\n2. Click expand Protection > Conditional Access select Policies.\n3. Ensure that a policy exists with the following criteria and is set to On:\no Under Users verify All users is included.\no Ensure that only documented user exclusions exist and that they are\nreviewed annually.\no Under Target resources verify Resources (formerly cloud apps)\nincludes Microsoft Intune Enrollment.\no Under Grant verify Require multifactor authentication or Require\nauthentication strength is checked.\no Under Session verify Sign-in frequency is set to Every time.\n4. Ensure Enable policy is set to On.\nNote: Break-glass accounts should be excluded from all Conditional Access policies.","Remediation":"To remediate using the UI:\n1. Navigate to the Microsoft Entra admin center https://entra.microsoft.com.\n2. Click expand Protection > Conditional Access select Policies.\n3. Create a new policy by selecting New policy.\no Under Users include All users.\no Under Target resources select Resources (formerly cloud apps),\nchoose Select resources and add Microsoft Intune Enrollment to\nthe list.\no Under Grant select Grant access.\no Check either Require multifactor authentication or Require\nauthentication strength.\no Under Session check Sign-in frequency and select Every time.\n4. Under Enable policy set it to Report-only until the organization is ready to\nenable it.\n5. Click Create.\nNote: If the Microsoft Intune Enrollment cloud app isn't available then it must be\ncreated. To add the app for new tenants, a Microsoft Entra administrator must create a\nservice principal object, with app ID d4ebce55-015a-49b5-a083-c84d1797ae8c, in\nPowerShell or Microsoft Graph.\nNote: Break-glass accounts should be excluded from all Conditional Access policies.","DefaultValue":"Sign-in frequency defaults to 90 days.","References":"1. https://learn.microsoft.com/en-us/entra/identity/conditional-access/concept-\nsession-lifetime#require-reauthentication-every-time\n2. https://www.blackhat.com/eu-24/briefings/schedule/#unveiling-the-power-of-\nintune-leveraging-intune-for-breaking-into-your-cloud-and-on-premise-42176\n3. https://www.glueckkanja.com/blog/security/2025/01/compliant-device-bypass-en/","CISControls":"[{\"version\": \"\", \"id\": \"6.3\", \"title\": \"Require MFA for Externally-Exposed Applications\", \"description\": \"v8 Require all externally-exposed enterprise or third-party applications to enforce - - MFA, where supported. Enforcing MFA through a directory service or SSO provider is a satisfactory implementation of this Safeguard.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]"}
CIS_METADATA_END #>
# Required Services: MgGraph
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()
    
    # Retrieve all Conditional Access Policies
    $policies = Get-MgIdentityConditionalAccessPolicy -All

    foreach ($policy in $policies) {
        # Check if the policy is enabled
        $isEnabled = $policy.State -eq "enabled"

        # Check if the policy includes all users
        $includesAllUsers = $policy.Conditions.Users.Include -contains "All"

        # Check if the policy targets Microsoft Intune Enrollment
        $targetsIntuneEnrollment = $policy.Conditions.Applications.Include -contains "d4ebce55-015a-49b5-a083-c84d1797ae8c"

        # Check if the policy requires MFA or authentication strength
        $requiresMFA = $policy.GrantControls.BuiltInControls -contains "mfa" -or $policy.GrantControls.BuiltInControls -contains "compliantDevice"

        # Check if the sign-in frequency is set to 'Every time'
        $signInFrequency = $policy.SessionControls.SignInFrequency.Value -eq "Every time"

        # Determine compliance
        $isCompliant = $isEnabled -and $includesAllUsers -and $targetsIntuneEnrollment -and $requiresMFA -and $signInFrequency

        # Add results to the array
        $resourceResults += @{
            PolicyName = $policy.DisplayName
            IsEnabled = $isEnabled
            IncludesAllUsers = $includesAllUsers
            TargetsIntuneEnrollment = $targetsIntuneEnrollment
            RequiresMFA = $requiresMFA
            SignInFrequency = $signInFrequency
            IsCompliant = $isCompliant
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
