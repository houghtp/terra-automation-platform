# Control: 5.2.2.9 - Ensure a managed device is required for
<# CIS_METADATA_START
{"RecommendationId":"5.2.2.9","Level":"L1","Title":"Ensure a managed device is required for authentication","Section":"5 Microsoft Entra admin center","SubSection":"5.2 Protection","ProfileApplicability":"- E3 Level 1\n- E5 Level 1","Description":"Conditional Access (CA) can be configured to enforce access based on the device's\ncompliance status or whether it is Entra hybrid joined. Collectively this allows CA to\nclassify devices as managed or unmanaged, providing more granular control over\nauthentication policies.\nWhen using Require device to be marked as compliant, the device must pass\nchecks configured in Compliance policies defined within Intune (Endpoint Manager).\nBefore these checks can be applied, the device must first be enrolled in Intune MDM.\nBy selecting Require Microsoft Entra hybrid joined device this means the\ndevice must first be synchronized from an on-premises Active Directory to qualify for\nauthentication.\nWhen configured to the recommended state below only one condition needs to be met\nfor the user to authenticate from the device. This functions as an \"OR\" operator.\nThe recommended state is:\n- Require device to be marked as compliant\n- Require Microsoft Entra hybrid joined device\n- Require one of the selected controls","Rationale":"\"Managed\" devices are considered more secure because they often have additional\nconfiguration hardening enforced through centralized management such as Intune or\nGroup Policy. These devices are also typically equipped with MDR/EDR, managed\npatching and alerting systems. As a result, they provide a safer environment for users to\nauthenticate and operate from.\nThis policy also ensures that attackers must first gain access to a compliant or trusted\ndevice before authentication is permitted, reducing the risk posed by compromised\naccount credentials. When combined with other distinct Conditional Access (CA)\npolicies, such as requiring multi-factor authentication, this adds one additional factor\nbefore authentication is permitted.\nNote: Avoid combining these two settings with other Grant settings in the same policy.\nIn a single policy you can only choose between Require all the selected\ncontrols or Require one of the selected controls, which limits the ability to\nintegrate this recommendation with others in this benchmark. CA policies function as an\n\"AND\" operator across multiple policies. The goal here is to both (Require MFA for all\nusers) AND (Require device to be marked as compliant OR Require Microsoft Entra\nhybrid joined device).","Impact":"Unmanaged devices will not be permitted as a valid authenticator. As a result this may\nrequire the organization to mature their device enrollment and management. The\nfollowing devices can be considered managed:\n- Entra hybrid joined from Active Directory\n- Entra joined and enrolled in Intune, with compliance policies\n- Entra registered and enrolled in Intune, with compliances policies\nIf Guest or external users are collaborating with the organization, they must either\nbe excluded or onboarded with a compliant device to authenticate. Failure to adequately\nsurvey the environment and test the Conditional Access (CA) policy in the Report-only\nstate could result in access disruptions for these guest users.","Audit":"To audit using the UI:\n1. Navigate to the Microsoft Entra admin center https://entra.microsoft.com.\n2. Click expand Protection > Conditional Access select Policies.\n3. Ensure that a policy exists with the following criteria and is set to On:\no Under Users verify All users is included.\no Ensure that only documented user exclusions exist and that they are\nreviewed annually.\no Under Target resources verify All resources (formerly 'All\ncloud apps') is selected.\no Ensure that only documented resource exclusions exist and that they are\nreviewed annually.\no Under Grant verify that only Require device to be marked as\ncompliant and Require Microsoft Entra hybrid joined device\nare checked.\no Under Grant verify Require one of the selected controls is\nselected.\n4. Ensure Enable policy is set to On.\nNote: Break-glass accounts should be excluded from all Conditional Access policies.","Remediation":"To remediate using the UI:\n1. Navigate to the Microsoft Entra admin center https://entra.microsoft.com.\n2. Click expand Protection > Conditional Access select Policies.\n3. Create a new policy by selecting New policy.\no Under Users include All users.\no Under Target resources include All resources (formerly 'All\ncloud apps').\no Under Grant select Grant access.\no Select only the checkboxes Require device to be marked as\ncompliant and Require Microsoft Entra hybrid joined device.\no Choose Require one of the selected controls and click Select at\nthe bottom.\n4. Under Enable policy set it to Report-only until the organization is ready to\nenable it.\n5. Click Create.\nNote: Guest user accounts, if collaborating with the organization, should be considered\nwhen testing this policy.","DefaultValue":"","References":"1. https://learn.microsoft.com/en-us/entra/identity/conditional-access/concept-\nconditional-access-grant#require-device-to-be-marked-as-compliant\n2. https://learn.microsoft.com/en-us/entra/identity/devices/concept-hybrid-join\n3. https://learn.microsoft.com/en-us/mem/intune/fundamentals/deployment-guide-\nenrollment","CISControls":"[{\"version\": \"\", \"id\": \"6.3\", \"title\": \"Require MFA for Externally-Exposed Applications\", \"description\": \"v8 Require all externally-exposed enterprise or third-party applications to enforce - - MFA, where supported. Enforcing MFA through a directory service or SSO provider is a satisfactory implementation of this Safeguard.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]"}
CIS_METADATA_END #>
# Required Services: MgGraph
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()
    
    # Retrieve Conditional Access Policies
    $caPolicies = Get-MgIdentityConditionalAccessPolicy -All

    foreach ($policy in $caPolicies) {
        # Check if the policy is enabled
        $isEnabled = $policy.State -eq "enabled"

        # Check if the policy includes all users
        $includesAllUsers = $policy.Conditions.Users.Include -contains "All"

        # Check if the policy targets all resources
        $targetsAllResources = $policy.Conditions.Applications.Include -contains "All"

        # Check if the policy requires device compliance or hybrid join
        $requiresDeviceCompliance = $policy.GrantControls.BuiltInControls -contains "compliantDevice"
        $requiresHybridJoin = $policy.GrantControls.BuiltInControls -contains "hybridAzureAD"

        # Check if the policy requires one of the selected controls
        $requiresOneControl = $policy.GrantControls.Operator -eq "OR"

        # Determine compliance
        $isCompliant = $isEnabled -and $includesAllUsers -and $targetsAllResources -and ($requiresDeviceCompliance -or $requiresHybridJoin) -and $requiresOneControl

        # Add results to array
        $resourceResults += @{
            PolicyName = $policy.DisplayName
            IsEnabled = $isEnabled
            IncludesAllUsers = $includesAllUsers
            TargetsAllResources = $targetsAllResources
            RequiresDeviceCompliance = $requiresDeviceCompliance
            RequiresHybridJoin = $requiresHybridJoin
            RequiresOneControl = $requiresOneControl
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
