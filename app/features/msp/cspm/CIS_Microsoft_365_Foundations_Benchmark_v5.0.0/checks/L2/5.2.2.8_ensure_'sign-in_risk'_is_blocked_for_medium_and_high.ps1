# Control: 5.2.2.8 - Ensure 'sign-in risk' is blocked for medium and high
<# CIS_METADATA_START
{"RecommendationId":"5.2.2.8","Level":"L2","Title":"Ensure 'sign-in risk' is blocked for medium and high risk","Section":"5 Microsoft Entra admin center","SubSection":"5.2 Protection","ProfileApplicability":"- E5 Level 2","Description":"Microsoft Entra ID Protection sign-in risk detects risks in real-time and offline. A risky\nsign-in is an indicator for a sign-in attempt that might not have been performed by the\nlegitimate owner of a user account.\nNote: While Identity Protection also provides two risk policies with limited conditions,\nMicrosoft highly recommends setting up risk-based policies in Conditional Access as\nopposed to the \"legacy method\" for the following benefits:\n- Enhanced diagnostic data\n- Report-only mode integration\n- Graph API support\n- Use more Conditional Access attributes like sign-in frequency in the policy","Rationale":"Sign-in risk is determined at the time of sign-in and includes criteria across both real-\ntime and offline detections for risk. Blocking sign-in to accounts that have risk can\nprevent undesired access from potentially compromised devices or unauthorized users.","Impact":"Sign-in risk is heavily dependent on detecting risk based on atypical behaviors. Due to\nthis it is important to run this policy in a report-only mode to better understand how the\norganization's environment and user activity may influence sign-in risk before turning\nthe policy on. Once it's understood what actions may trigger a medium or high sign-in\nrisk event I.T. can then work to create an environment to reduce false positives. For\nexample, employees might be required to notify security personnel when they intend to\ntravel with intent to access work resources.\nNote: Break-glass accounts should always be excluded from risk detection.","Audit":"To audit using the UI:\n1. Navigate to the Microsoft Entra admin center https://entra.microsoft.com.\n2. Click expand Protection > Conditional Access select Policies.\n3. Ensure that a policy exists with the following criteria and is set to On:\no Under Users verify All users is included.\no Ensure that only documented user exclusions exist and that they are\nreviewed annually.\no Under Target resources verify All resources (formerly 'All\ncloud apps') is selected with no exclusions.\no Under Conditions verify Sign-in risk values of High and Medium are\nselected.\no Under Grant verify Block access is selected.\n4. Ensure Enable policy is set to On.\nNote: Break-glass accounts should be excluded from all Conditional Access policies.","Remediation":"To remediate using the UI:\n1. Navigate to the Microsoft Entra admin center https://entra.microsoft.com.\n2. Click expand Protection > Conditional Access select Policies.\n3. Create a new policy by selecting New policy.\n4. Set the following conditions within the policy.\no Under Users include All users.\no Under Target resources include All resources (formerly 'All\ncloud apps') and do not set any exclusions.\no Under Conditions choose Sign-in risk values of High and Medium\nand click Done.\no Under Grant choose Block access and click Select.\n5. Under Enable policy set it to Report-only until the organization is ready to\nenable it.\n6. Click Create.\nNote: Break-glass accounts should be excluded from all Conditional Access policies.","DefaultValue":"","References":"1. https://learn.microsoft.com/en-us/entra/id-protection/concept-identity-protection-\nrisks#risk-detections-mapped-to-riskeventtype","CISControls":"[{\"version\": \"\", \"id\": \"13.3\", \"title\": \"Deploy a Network Intrusion Detection Solution\", \"description\": \"v8 Deploy a network intrusion detection solution on enterprise assets, where - - appropriate. Example implementations include the use of a Network Intrusion Detection System (NIDS) or equivalent cloud service provider (CSP) service.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]"}
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
        # Check if the policy includes all users
        $includesAllUsers = $policy.Conditions.Users.Include -contains "All"

        # Check if the policy targets all resources
        $targetsAllResources = $policy.Conditions.Applications.Include -contains "All"

        # Check if the policy has sign-in risk conditions set to Medium and High
        $signInRiskConditions = $policy.Conditions.SignInRiskLevels -contains "medium" -and $policy.Conditions.SignInRiskLevels -contains "high"

        # Check if the policy grants block access
        $grantsBlockAccess = $policy.GrantControls.BuiltInControls -contains "Block"

        # Check if the policy is enabled
        $isPolicyEnabled = $policy.State -eq "enabled"

        # Determine compliance for this policy
        $isCompliant = $includesAllUsers -and $targetsAllResources -and $signInRiskConditions -and $grantsBlockAccess -and $isPolicyEnabled

        # Add the result for this policy to the results array
        $resourceResults += @{
            PolicyName = $policy.DisplayName
            IncludesAllUsers = $includesAllUsers
            TargetsAllResources = $targetsAllResources
            SignInRiskConditions = $signInRiskConditions
            GrantsBlockAccess = $grantsBlockAccess
            IsPolicyEnabled = $isPolicyEnabled
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
