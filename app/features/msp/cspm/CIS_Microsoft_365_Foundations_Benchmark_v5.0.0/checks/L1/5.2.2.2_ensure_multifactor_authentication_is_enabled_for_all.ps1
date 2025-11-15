# Control: 5.2.2.2 - Ensure multifactor authentication is enabled for all
<# CIS_METADATA_START
{"RecommendationId":"5.2.2.2","Level":"L1","Title":"Ensure multifactor authentication is enabled for all users","Section":"5 Microsoft Entra admin center","SubSection":"5.2 Protection","ProfileApplicability":"- E3 Level 1\n- E5 Level 1","Description":"Enable multifactor authentication for all users in the Microsoft 365 tenant. Users will be\nprompted to authenticate with a second factor upon logging in to Microsoft 365 services.\nThe second factor is most commonly a text message to a registered mobile phone\nnumber where they type in an authorization code, or with a mobile application like\nMicrosoft Authenticator.","Rationale":"Multifactor authentication requires an individual to present a minimum of two separate\nforms of authentication before access is granted. Multifactor authentication provides\nadditional assurance that the individual attempting to gain access is who they claim to\nbe. With multifactor authentication, an attacker would need to compromise at least two\ndifferent authentication mechanisms, increasing the difficulty of compromise and thus\nreducing the risk.","Impact":"Implementation of multifactor authentication for all users will necessitate a change to\nuser routine. All users will be required to enroll in multifactor authentication using phone,\nSMS, or an authentication application. After enrollment, use of multifactor authentication\nwill be required for future authentication to the environment.\nExternal identities that attempt to access documents that utilize Purview Information\nProtection (Sensitivity Labels) will find their access disrupted. In order to mitigate this\ncreate an exclusion for Microsoft Rights Management Services ID: 00000012-\n0000-0000-c000-000000000000\nNote: Organizations that struggle to enforce MFA globally due to budget constraints\npreventing the provision of company-owned mobile devices to every user, or due to\nregulations, unions, or policies that prevent forcing end users to use their personal\ndevices, have another option. FIDO2 security keys can be used as an alternative. They\nare more secure, phishing-resistant, and affordable for organizations to issue to every\nend user.","Audit":"To audit using the UI:\n1. Navigate to the Microsoft Entra admin center https://entra.microsoft.com.\n2. Click expand Protection > Conditional Access select Policies.\n3. Ensure that a policy exists with the following criteria and is set to On:\no Under Users verify All users is included.\no Ensure that only documented user exclusions exist and that they are\nreviewed annually.\no Under Target resources verify All resources (formerly 'All\ncloud apps') is selected with no exclusions.\no Under Grant verify Grant Access and either Require multifactor\nauthentication or Require authentication strength is checked.\n4. Ensure Enable policy is set to On.\nNote: Break-glass accounts should be excluded from all Conditional Access policies.","Remediation":"To remediate using the UI:\n1. Navigate to the Microsoft Entra admin center https://entra.microsoft.com.\n2. Click expand Protection > Conditional Access select Policies.\n3. Click New policy.\no Under Users include All users.\no Under Target resources include All resources (formerly 'All\ncloud apps') and do not create any exclusions.\no Under Grant select Grant Access and check either Require\nmultifactor authentication or Require authentication\nstrength.\no Click Select at the bottom of the pane.\n4. Under Enable policy set it to Report-only until the organization is ready to\nenable it.\n5. Click Create.\nNote: Break-glass accounts should be excluded from all Conditional Access policies.","DefaultValue":"","References":"1. https://learn.microsoft.com/en-us/entra/identity/conditional-access/howto-\nconditional-access-policy-all-users-mfa","CISControls":"[{\"version\": \"\", \"id\": \"6.3\", \"title\": \"Require MFA for Externally-Exposed Applications\", \"description\": \"v8 Require all externally-exposed enterprise or third-party applications to enforce - - MFA, where supported. Enforcing MFA through a directory service or SSO provider is a satisfactory implementation of this Safeguard.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"\", \"id\": \"16.3\", \"title\": \"Require Multi-factor Authentication\", \"description\": \"Require multi-factor authentication for all user accounts, on all systems, - - whether managed onsite or by a third-party provider.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]"}
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
        $isEnabled = $policy.State -eq "enabled"
        
        # Check if the policy includes all users
        $includesAllUsers = $policy.Conditions.Users.Include -contains "All"
        
        # Check if the policy targets all cloud apps
        $targetsAllResources = $policy.Conditions.Applications.Include -contains "All"
        
        # Check if the policy requires MFA
        $requiresMFA = $policy.GrantControls.BuiltInControls -contains "Mfa"
        
        # Determine compliance for this policy
        $isCompliant = $isEnabled -and $includesAllUsers -and $targetsAllResources -and $requiresMFA
        
        # Add policy result to the results array
        $resourceResults += @{
            PolicyName = $policy.DisplayName
            IsEnabled = $isEnabled
            IncludesAllUsers = $includesAllUsers
            TargetsAllResources = $targetsAllResources
            RequiresMFA = $requiresMFA
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
