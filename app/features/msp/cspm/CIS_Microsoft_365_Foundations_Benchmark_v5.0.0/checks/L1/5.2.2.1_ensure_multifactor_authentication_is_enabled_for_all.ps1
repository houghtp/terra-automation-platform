# Control: 5.2.2.1 - Ensure multifactor authentication is enabled for all
<# CIS_METADATA_START
{"RecommendationId":"5.2.2.1","Level":"L1","Title":"Ensure multifactor authentication is enabled for all users in administrative roles","Section":"5 Microsoft Entra admin center","SubSection":"5.2 Protection","ProfileApplicability":"- E3 Level 1\n- E5 Level 1","Description":"Multifactor authentication is a process that requires an additional form of identification\nduring the sign-in process, such as a code from a mobile device or a fingerprint scan, to\nenhance security.\nEnsure users in administrator roles have MFA capabilities enabled.","Rationale":"Multifactor authentication requires an individual to present a minimum of two separate\nforms of authentication before access is granted. Multifactor authentication provides\nadditional assurance that the individual attempting to gain access is who they claim to\nbe. With multifactor authentication, an attacker would need to compromise at least two\ndifferent authentication mechanisms, increasing the difficulty of compromise and thus\nreducing the risk.","Impact":"Implementation of multifactor authentication for all users in administrative roles will\nnecessitate a change to user routine. All users in administrative roles will be required to\nenroll in multifactor authentication using phone, SMS, or an authentication application.\nAfter enrollment, use of multifactor authentication will be required for future access to\nthe environment.","Audit":"To audit using the UI:\n1. Navigate to the Microsoft Entra admin center https://entra.microsoft.com.\n2. Click to expand Protection > Conditional Access select Policies.\n3. Ensure that a policy exists with the following criteria and is set to On:\no Under Users verify Directory roles specific to administrators are\nincluded.\no Ensure that only documented user exclusions exist and that they are\nreviewed annually.\no Under Target resources verify All resources (formerly 'All\ncloud apps') is selected with no exclusions.\no Under Grant verify Grant Access is on and either Require\nmultifactor authentication or Require authentication strength\nis checked.\n4. Ensure Enable policy is set to On.\nNote: A list of Directory roles can be found in the Remediation section.\nNote: Break-glass accounts should be excluded from all Conditional Access policies.","Remediation":"To remediate using the UI:\n1. Navigate to the Microsoft Entra admin center https://entra.microsoft.com.\n2. Click expand Protection > Conditional Access select Policies.\n3. Click New policy.\no Under Users include Select users and groups and check Directory\nroles.\no At a minimum, include the directory roles listed below in this section of the\ndocument.\no Under Target resources include All resources (formerly 'All\ncloud apps') and do not create any exclusions.\no Under Grant select Grant Access and check either Require\nmultifactor authentication or Require authentication\nstrength.\no Click Select at the bottom of the pane.\n4. Under Enable policy set it to Report-only until the organization is ready to\nenable it.\n5. Click Create.\nAt minimum these directory roles should be included for MFA:\n- Application administrator\n- Authentication administrator\n- Billing administrator\n- Cloud application administrator\n- Conditional Access administrator\n- Exchange administrator\n- Global administrator\n- Global reader\n- Helpdesk administrator\n- Password administrator\n- Privileged authentication administrator\n- Privileged role administrator\n- Security administrator\n- SharePoint administrator\n- User administrator\nNote: Report-only is an acceptable first stage when introducing any CA policy. The\ncontrol, however, is not complete until the policy is on.","DefaultValue":"","References":"1. https://learn.microsoft.com/en-us/entra/identity/conditional-access/howto-\nconditional-access-policy-admin-mfa","CISControls":"[{\"version\": \"\", \"id\": \"6.5\", \"title\": \"Require MFA for Administrative Access\", \"description\": \"Require MFA for all administrative access accounts, where supported, on all - - - enterprise assets, whether managed on-site or through a third-party provider.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"v8\", \"id\": \"16.3\", \"title\": \"Require Multi-factor Authentication\", \"description\": \"Require multi-factor authentication for all user accounts, on all systems, - - whether managed onsite or by a third-party provider.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]"}
CIS_METADATA_END #>
# Required Services: MgGraph
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()
    
    # Retrieve Conditional Access Policies
    $policies = Get-MgIdentityConditionalAccessPolicy -All

    # Define required directory roles for MFA
    $requiredRoles = @(
        "Application administrator",
        "Authentication administrator",
        "Billing administrator",
        "Cloud application administrator",
        "Conditional Access administrator",
        "Exchange administrator",
        "Global administrator",
        "Global reader",
        "Helpdesk administrator",
        "Password administrator",
        "Privileged authentication administrator",
        "Privileged role administrator",
        "Security administrator",
        "SharePoint administrator",
        "User administrator"
    )

    # Check each policy for compliance
    foreach ($policy in $policies) {
        $isCompliant = $false
        $policyDetails = Get-MgIdentityConditionalAccessPolicy -ConditionalAccessPolicyId $policy.Id

        # Check if policy is enabled
        if ($policyDetails.State -eq "enabled") {
            # Check if required roles are included
            $includedRoles = $policyDetails.Conditions.Users.IncludeRoles
            $rolesCompliant = $requiredRoles | ForEach-Object { $_ -in $includedRoles }

            # Check if all resources are targeted
            $allResourcesTargeted = $policyDetails.Conditions.Applications.IncludeApplications -contains "All"

            # Check if MFA is required
            $mfaRequired = $policyDetails.GrantControls.BuiltInControls -contains "Mfa"

            # Determine compliance
            $isCompliant = $rolesCompliant -and $allResourcesTargeted -and $mfaRequired
        }

        # Add policy result to results array
        $resourceResults += @{
            PolicyName = $policy.DisplayName
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
