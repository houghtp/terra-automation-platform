# Control: 5.2.2.6 - Enable Identity Protection user risk policies
<# CIS_METADATA_START
{"RecommendationId":"5.2.2.6","Level":"L1","Title":"Enable Identity Protection user risk policies","Section":"5 Microsoft Entra admin center","SubSection":"5.2 Protection","ProfileApplicability":"- E5 Level 1","Description":"Microsoft Entra ID Protection user risk policies detect the probability that a user account\nhas been compromised.\nNote: While Identity Protection also provides two risk policies with limited conditions,\nMicrosoft highly recommends setting up risk-based policies in Conditional Access as\nopposed to the \"legacy method\" for the following benefits:\n- Enhanced diagnostic data\n- Report-only mode integration\n- Graph API support\n- Use more Conditional Access attributes like sign-in frequency in the policy","Rationale":"With the user risk policy turned on, Entra ID protection detects the probability that a user\naccount has been compromised. Administrators can configure a user risk conditional\naccess policy to automatically respond to a specific user risk level.","Impact":"Upon policy activation, account access will be either blocked or the user will be required\nto use multi-factor authentication (MFA) and change their password. Users without\nregistered MFA will be denied access, necessitating an admin to recover the account.\nTo avoid inconvenience, it is advised to configure the MFA registration policy for all\nusers under the User Risk policy.\nAdditionally, users identified in the Risky Users section will be affected by this policy. To\ngain a better understanding of the impact on the organization's environment, the list of\nRisky Users should be reviewed before enforcing the policy.","Audit":"To audit using the UI:\n1. Navigate to the Microsoft Entra admin center https://entra.microsoft.com.\n2. Click expand Protection > Conditional Access select Policies.\n3. Ensure that a policy exists with the following criteria and is set to On:\no Under Users verify All users is included.\no Ensure that only documented user exclusions exist and that they are\nreviewed annually.\no Under Target resources verify All resources (formerly 'All\ncloud apps') is selected.\no Under Conditions verify User risk is set to High.\no Under Grant verify Grant access is selected and either Require\nmultifactor authentication or Require authentication strength\nare checked. Then verify Require password change is checked.\no Under Session ensure Sign-in frequency is set to Every time.\n4. Ensure Enable policy is set to On.\nNote: Break-glass accounts should be excluded from all Conditional Access policies.","Remediation":"To remediate using the UI:\n1. Navigate to the Microsoft Entra admin center https://entra.microsoft.com.\n2. Click expand Protection > Conditional Access select Policies.\n3. Create a new policy by selecting New policy.\n4. Set the following conditions within the policy:\no Under Users choose All users\no Under Target resources choose All resources (formerly 'All\ncloud apps')\no Under Conditions choose User risk then Yes and select the user risk\nlevel High.\no Under Grant select Grant access then check Require multifactor\nauthentication or Require authentication strength. Finally check\nRequire password change.\no Under Session set Sign-in frequency to Every time.\no Click Select.\n5. Under Enable policy set it to Report-only until the organization is ready to\nenable it.\n6. Click Create or Save.\nNote: Break-glass accounts should be excluded from all Conditional Access policies.","DefaultValue":"","References":"1. https://learn.microsoft.com/en-us/entra/id-protection/howto-identity-protection-\nrisk-feedback\n2. https://learn.microsoft.com/en-us/entra/id-protection/concept-identity-protection-\nrisks","CISControls":"[{\"version\": \"\", \"id\": \"13.3\", \"title\": \"Deploy a Network Intrusion Detection Solution\", \"description\": \"v8 Deploy a network intrusion detection solution on enterprise assets, where - - appropriate. Example implementations include the use of a Network Intrusion Detection System (NIDS) or equivalent cloud service provider (CSP) service.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"\", \"id\": \"16.13\", \"title\": \"Alert on Account Login Behavior Deviation\", \"description\": \"Alert when users deviate from normal login behavior, such as time-of-day, - workstation location and duration.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]"}
CIS_METADATA_END #>
# Required Services: MgGraph
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()
    
    # Retrieve Conditional Access Policies
    $policies = Get-MgIdentityConditionalAccessPolicy -All

    foreach ($policy in $policies) {
        # Check if the policy is enabled
        $isEnabled = $policy.State -eq 'enabled'
        
        # Check if the policy includes all users
        $includesAllUsers = $policy.Conditions.Users.Include -contains 'All'
        
        # Check if the policy targets all resources
        $targetsAllResources = $policy.Conditions.Applications.Include -contains 'All'
        
        # Check if the user risk condition is set to High
        $userRiskCondition = $policy.Conditions.UserRiskLevels -contains 'high'
        
        # Check if the grant controls are set correctly
        $grantControls = $policy.GrantControls.BuiltInControls
        $requiresMFA = $grantControls -contains 'mfa'
        $requiresPasswordChange = $grantControls -contains 'passwordChange'
        
        # Check if the session control for sign-in frequency is set to every time
        $sessionControls = $policy.SessionControls
        $signInFrequency = $sessionControls.SignInFrequency.Equals('Every time', 'InvariantCultureIgnoreCase')
        
        # Determine compliance
        $isCompliant = $isEnabled -and $includesAllUsers -and $targetsAllResources -and $userRiskCondition -and $requiresMFA -and $requiresPasswordChange -and $signInFrequency
        
        # Add results to the array
        $resourceResults += @{
            PolicyName = $policy.DisplayName
            IsEnabled = $isEnabled
            IncludesAllUsers = $includesAllUsers
            TargetsAllResources = $targetsAllResources
            UserRiskCondition = $userRiskCondition
            RequiresMFA = $requiresMFA
            RequiresPasswordChange = $requiresPasswordChange
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
