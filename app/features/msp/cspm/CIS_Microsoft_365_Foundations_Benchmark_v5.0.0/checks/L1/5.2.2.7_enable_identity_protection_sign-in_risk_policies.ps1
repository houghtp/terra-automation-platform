# Control: 5.2.2.7 - Enable Identity Protection sign-in risk policies
<# CIS_METADATA_START
{"RecommendationId":"5.2.2.7","Level":"L1","Title":"Enable Identity Protection sign-in risk policies","Section":"5 Microsoft Entra admin center","SubSection":"5.2 Protection","ProfileApplicability":"- E5 Level 1","Description":"Microsoft Entra ID Protection sign-in risk detects risks in real-time and offline. A risky\nsign-in is an indicator for a sign-in attempt that might not have been performed by the\nlegitimate owner of a user account.\nNote: While Identity Protection also provides two risk policies with limited conditions,\nMicrosoft highly recommends setting up risk-based policies in Conditional Access as\nopposed to the \"legacy method\" for the following benefits:\n- Enhanced diagnostic data\n- Report-only mode integration\n- Graph API support\n- Use more Conditional Access attributes like sign-in frequency in the policy","Rationale":"Turning on the sign-in risk policy ensures that suspicious sign-ins are challenged for\nmulti-factor authentication.","Impact":"When the policy triggers, the user will need MFA to access the account. In the case of a\nuser who hasn't registered MFA on their account, they would be blocked from accessing\ntheir account. It is therefore recommended that the MFA registration policy be\nconfigured for all users who are a part of the Sign-in Risk policy.","Audit":"To ensure Sign-In a risk policy is enabled:\n1. Navigate to the Microsoft Entra admin center https://entra.microsoft.com.\n2. Click expand Protection > Conditional Access select Policies.\n3. Ensure that a policy exists with the following criteria and is set to On:\no Under Users verify All users is included.\no Ensure that only documented user exclusions exist and that they are\nreviewed annually.\no Under Target resources verify All resources (formerly 'All\ncloud apps') is selected.\no Under Conditions verify Sign-in risk is set to Yes ensuring High and\nMedium are selected.\no Under Grant verify grant Grant access is selected and Require\nmultifactor authentication checked.\no Under Session verify Sign-in Frequency is set to Every time.\n4. Ensure Enable policy is set to On.\nNote: Break-glass accounts should be excluded from all Conditional Access policies.","Remediation":"To configure a Sign-In risk policy, use the following steps:\n1. Navigate to the Microsoft Entra admin center https://entra.microsoft.com.\n2. Click expand Protection > Conditional Access select Policies.\n3. Create a new policy by selecting New policy.\n4. Set the following conditions within the policy.\no Under Users choose All users.\no Under Target resources choose All resources (formerly 'All\ncloud apps').\no Under Conditions choose Sign-in risk then Yes and check the risk\nlevel boxes High and Medium.\no Under Grant click Grant access then select Require multifactor\nauthentication.\no Under Session select Sign-in Frequency and set to Every time.\no Click Select.\n5. Under Enable policy set it to Report-only until the organization is ready to\nenable it.\n6. Click Create.\nNote: Break-glass accounts should be excluded from all Conditional Access policies.","DefaultValue":"","References":"1. https://learn.microsoft.com/en-us/entra/id-protection/howto-identity-protection-\nrisk-feedback\n2. https://learn.microsoft.com/en-us/entra/id-protection/concept-identity-protection-\nrisks","CISControls":"[{\"version\": \"\", \"id\": \"13.3\", \"title\": \"Deploy a Network Intrusion Detection Solution\", \"description\": \"v8 Deploy a network intrusion detection solution on enterprise assets, where - - appropriate. Example implementations include the use of a Network Intrusion Detection System (NIDS) or equivalent cloud service provider (CSP) service.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"\", \"id\": \"16.13\", \"title\": \"Alert on Account Login Behavior Deviation\", \"description\": \"Alert when users deviate from normal login behavior, such as time-of-day, - workstation location and duration.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]"}
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
        $isEnabled = $policy.State -eq "Enabled"
        
        # Check if the policy includes all users
        $includesAllUsers = $policy.Conditions.Users.Include -contains "All"
        
        # Check if the policy targets all resources
        $targetsAllResources = $policy.Conditions.Applications.Include -contains "All"
        
        # Check if the sign-in risk condition is set to High and Medium
        $signInRiskCondition = $policy.Conditions.SignInRiskLevels -contains "high" -and $policy.Conditions.SignInRiskLevels -contains "medium"
        
        # Check if the grant control requires MFA
        $requiresMFA = $policy.GrantControls.BuiltInControls -contains "mfa"
        
        # Check if the session control is set to require sign-in frequency every time
        $signInFrequency = $policy.SessionControls.SignInFrequency -eq "EveryTime"
        
        # Determine compliance
        $isCompliant = $isEnabled -and $includesAllUsers -and $targetsAllResources -and $signInRiskCondition -and $requiresMFA -and $signInFrequency
        
        # Add results to the array
        $resourceResults += @{
            PolicyName = $policy.DisplayName
            IsEnabled = $isEnabled
            IncludesAllUsers = $includesAllUsers
            TargetsAllResources = $targetsAllResources
            SignInRiskCondition = $signInRiskCondition
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
